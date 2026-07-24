from flask import Flask, request, redirect, jsonify, session, render_template
import subprocess, re, json, os, secrets, time

recent_proxy_activity = {}

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
def find_cfg_path():
    possible_paths = [
        "/usr/local/frp/frpc.toml",
        "/etc/frp/frpc.toml",
        "/etc/frpc.toml",
        "/usr/local/etc/frpc.toml",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "frpc.toml")
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return "/usr/local/frp/frpc.toml"

CFG = find_cfg_path()

def get_webserver_info():
    addr = "127.0.0.1"
    port = 7400
    user = "admin"
    password = "admin"
    
    if os.path.exists(CFG):
        try:
            with open(CFG, "r") as f:
                c = f.read()
            pm = re.search(r'\[webServer\][^\[]*port\s*=\s*(\d+)', c, re.DOTALL) or re.search(r'admin_port\s*=\s*(\d+)', c)
            if pm: port = int(pm.group(1))
            
            am = re.search(r'\[webServer\][^\[]*addr\s*=\s*"([^"]+)"', c, re.DOTALL) or re.search(r'admin_addr\s*=\s*"([^"]+)"', c)
            if am: addr = am.group(1)
            
            um = re.search(r'\[webServer\][^\[]*user\s*=\s*"([^"]+)"', c, re.DOTALL) or re.search(r'admin_user\s*=\s*"([^"]+)"', c)
            if um: user = um.group(1)
            
            pwdm = re.search(r'\[webServer\][^\[]*password\s*=\s*"([^"]+)"', c, re.DOTALL) or re.search(r'admin_pwd\s*=\s*"([^"]+)"', c)
            if pwdm: password = pwdm.group(1)
        except Exception as e:
            print(f"Error reading webserver info: {e}")
            
    if addr in ["0.0.0.0", "::"]:
        addr = "127.0.0.1"
    return addr, port, user, password

def ensure_webserver_in_config():
    if not os.path.exists(CFG):
        return False
    try:
        with open(CFG, 'r') as f:
            content = f.read()
        if '[webServer]' not in content and 'admin_port' not in content and 'adminPort' not in content:
            web_cfg = '\n\n[webServer]\naddr = "127.0.0.1"\nport = 7400\nuser = "admin"\npassword = "admin"\n'
            with open(CFG, 'a') as f:
                f.write(web_cfg)
            subprocess.run(["sudo", "systemctl", "restart", "frpc"], capture_output=True)
            return True
    except Exception as e:
        print(f"Failed to ensure webServer: {e}")
    return False

def get_system_traffic():
    rx_total = 0
    tx_total = 0
    server_ip = None
    if os.path.exists(CFG):
        try:
            with open(CFG, 'r') as f:
                cfg_txt = f.read()
            m = re.search(r'serverAddr\s*=\s*"([^"]+)"', cfg_txt) or re.search(r'server_addr\s*=\s*"([^"]+)"', cfg_txt)
            if m:
                server_ip = m.group(1).strip()
        except Exception:
            pass
            
    try:
        cmd = ["ss", "-t", "-i", "state", "established"]
        out = subprocess.check_output(cmd, text=True, timeout=2.0)
        lines = out.split("\n")
        for i in range(len(lines)):
            line = lines[i]
            if (server_ip and server_ip in line) or "frpc" in line:
                info_line = lines[i+1] if i+1 < len(lines) else ""
                sent_m = re.search(r'bytes_sent:(\d+)', info_line)
                recv_m = re.search(r'bytes_received:(\d+)', info_line)
                if sent_m:
                    tx_total += int(sent_m.group(1))
                if recv_m:
                    rx_total += int(recv_m.group(1))
    except Exception as e:
        print(f"Error extracting FRP socket traffic: {e}")

    # 兜底策略：如果未能从 FRP 专有套接字提取到数据，则降级读取系统网口
    if rx_total == 0 and tx_total == 0:
        try:
            if os.path.exists('/proc/net/dev'):
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()
                for line in lines[2:]:
                    parts = line.strip().split(':')
                    if len(parts) != 2:
                        continue
                    iface = parts[0].strip()
                    if iface.startswith('lo') or iface.startswith('veth') or iface.startswith('br-') or iface.startswith('docker'):
                        continue
                    stats = parts[1].split()
                    if len(stats) >= 10:
                        rx_total += int(stats[0])
                        tx_total += int(stats[8])
        except Exception as e:
            print(f"Error reading system fallback traffic: {e}")

    return rx_total, tx_total


@app.route("/api/tunnels")
def api_tunnels():
    import urllib.request
    import base64
    import json
    
    addr, port, user, password = get_webserver_info()
    server_ip = "43.108.18.47"
    if os.path.exists(CFG):
        try:
            with open(CFG, "r") as f:
                c_text = f.read()
                m_ip = re.search(r'serverAddr\s*=\s*[\"\']([^\"\']+)[\"\']', c_text)
                if m_ip:
                    server_ip = m_ip.group(1)
        except Exception:
            pass

    url = f"http://{addr}:{port}/api/status"
    req = urllib.request.Request(url)
    auth_str = f"{user}:{password}"
    auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    req.add_header("Authorization", f"Basic {auth_bytes}")
    
    try:
        with urllib.request.urlopen(req, timeout=3.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                tunnels = {}
                type_counts = {"tcp": 0, "udp": 0, "http": 0, "https": 0}
                total_conns = 0

                # 预先获取属于各代理的实时 TCP 连接 (结合 ESTABLISHED 精确数与 TIME-WAIT 活跃状态)
                estab_counts = {}
                active_counts = {}
                
                # 构建本地与远程端口到代理名称的双向映射
                port_map = {}
                for category in ["tcp", "udp", "http", "https", "stcp", "xtcp"]:
                    if category in data and isinstance(data[category], list):
                        for item in data[category]:
                            if not isinstance(item, dict):
                                continue
                            la = item.get("local_addr", "")
                            ra = item.get("remote_addr", "")
                            name = item.get("name", "")
                            if la and ":" in la and name:
                                port_map[la.split(":")[-1]] = name
                            if ra and ":" in ra and name:
                                port_map[ra.split(":")[-1]] = name

                try:
                    cmd = ["ss", "-t", "-a", "-n", "-p"]
                    ss_out = subprocess.check_output(cmd, text=True, timeout=1.5)
                    for line in ss_out.split("\n"):
                        parts = line.split()
                        if len(parts) >= 5:
                            state = parts[0]
                            # 过滤掉侦听端口状态 (LISTEN/UNCONN)
                            if state in ["LISTEN", "UNCONN"]:
                                continue
                            local_ap = parts[3]
                            remote_ap = parts[4]
                            # 仅排除 FRP 服务器的主控制管道 (端口 7000/5443)
                            if server_ip and (remote_ap.endswith(":7000") or local_ap.endswith(":7000") or remote_ap.endswith(":5443")):
                                continue
                            
                            for port, name in port_map.items():
                                if local_ap.endswith(":" + port) or remote_ap.endswith(":" + port):
                                    active_counts[name] = active_counts.get(name, 0) + 1
                                    if state == "ESTAB":
                                        estab_counts[name] = estab_counts.get(name, 0) + 1
                except Exception as e:
                    print(f"Error checking frpc socket connections: {e}")

                for category in ["tcp", "udp", "http", "https", "stcp", "xtcp"]:
                    if category in data and isinstance(data[category], list):
                        if category in type_counts:
                            type_counts[category] = len(data[category])
                        for item in data[category]:
                            if not isinstance(item, dict):
                                continue
                            status = item.get("status", "unknown")
                            name = item.get("name", "")
                            
                            # 精准计算活动连接数：长连接显示实际 ESTABLISHED 数，短连接(HTTP)展示内核 TIME-WAIT 动态活跃状态
                            cur_conns = 0
                            if "cur_conns" in item and item["cur_conns"] is not None:
                                try:
                                    cur_conns = int(item["cur_conns"])
                                except Exception:
                                    cur_conns = 0
                            elif "curConns" in item and item["curConns"] is not None:
                                try:
                                    cur_conns = int(item["curConns"])
                                except Exception:
                                    cur_conns = 0
                            elif status == "running":
                                e_cnt = estab_counts.get(name, 0)
                                a_cnt = active_counts.get(name, 0)
                                if e_cnt > 0:
                                    cur_conns = e_cnt
                                elif a_cnt > 0:
                                    cur_conns = 1
                                else:
                                    cur_conns = 0

                            traffic_in = item.get("traffic_in") or item.get("trafficIn") or 0
                            traffic_out = item.get("traffic_out") or item.get("trafficOut") or 0
                            try:
                                traffic_in = int(traffic_in)
                            except Exception:
                                traffic_in = 0
                            try:
                                traffic_out = int(traffic_out)
                            except Exception:
                                traffic_out = 0

                            total_conns += cur_conns

                            tunnels[item.get("name", "")] = {
                                "status": status,
                                "err": item.get("err", ""),
                                "cur_conns": cur_conns,
                                "traffic_in": traffic_in,
                                "traffic_out": traffic_out
                            }

                total_traffic_in, total_traffic_out = get_system_traffic()
                return jsonify({
                    "success": True, 
                    "tunnels": tunnels, 
                    "type_counts": type_counts,
                    "total_conns": total_conns,
                    "total_traffic_in": total_traffic_in,
                    "total_traffic_out": total_traffic_out
                })
    except Exception as e:
        ensure_webserver_in_config()
        return jsonify({"success": False, "error": f"控制台未连通({addr}:{port}): {str(e)}"})

AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth.json")

def get_auth_credentials():
    if not os.path.exists(AUTH_FILE):
        default_username = "admin"
        default_password = secrets.token_hex(4)  # 8位随机强密码
        creds = {"username": default_username, "password": default_password, "auth_enabled": True}
        with open(AUTH_FILE, "w") as f:
            json.dump(creds, f)
        print(f"==================================================")
        print(f"🔑 FRP Manager Initialized Credentials:")
        print(f"👤 Username: {default_username}")
        print(f"🔒 Password: {default_password}")
        print(f"📝 Credentials saved to: {AUTH_FILE}")
        print(f"==================================================")
        return creds
    try:
        with open(AUTH_FILE) as f:
            data = json.load(f)
            if "auth_enabled" not in data:
                data["auth_enabled"] = True
            return data
    except:
        return {"username": "admin", "password": "admin_password", "auth_enabled": True}

# 确保启动时自动初始化或读取凭证并在后台打印
get_auth_credentials()

# ==================== FRPS 服务端 Dashboard API 对接 (方案二) ====================
FRPS_DASHBOARD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frps_dashboard.json")

def get_frps_dashboard_config():
    default_addr = "127.0.0.1"
    if os.path.exists(CFG):
        try:
            with open(CFG, "r") as f:
                c_text = f.read()
                m_ip = re.search(r'serverAddr\s*=\s*[\"\']([^\"\']+)[\"\']', c_text)
                if m_ip:
                    default_addr = m_ip.group(1)
        except Exception:
            pass

    if not os.path.exists(FRPS_DASHBOARD_FILE):
        cfg = {
            "dash_addr": default_addr,
            "dash_port": 7500,
            "dash_user": "admin",
            "dash_password": "admin",
            "dash_enabled": False
        }
        try:
            with open(FRPS_DASHBOARD_FILE, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f"Error saving default frps dashboard config: {e}")
        return cfg
    try:
        with open(FRPS_DASHBOARD_FILE, "r") as f:
            data = json.load(f)
            if "dash_enabled" not in data:
                data["dash_enabled"] = False
            return data
    except Exception:
        return {
            "dash_addr": default_addr,
            "dash_port": 7500,
            "dash_user": "admin",
            "dash_password": "admin",
            "dash_enabled": False
        }

@app.route("/api/frps/config", methods=["GET", "POST"])
def api_frps_config():
    if request.method == "POST":
        try:
            data = request.json or {}
            dash_addr = data.get("dash_addr", "").strip()
            dash_port = int(data.get("dash_port", 7500))
            dash_user = data.get("dash_user", "").strip()
            dash_password = data.get("dash_password", "").strip()
            dash_enabled = bool(data.get("dash_enabled", False))

            cfg = {
                "dash_addr": dash_addr,
                "dash_port": dash_port,
                "dash_user": dash_user,
                "dash_password": dash_password,
                "dash_enabled": dash_enabled
            }
            with open(FRPS_DASHBOARD_FILE, "w") as f:
                json.dump(cfg, f, indent=2)
            return jsonify({"success": True, "config": cfg})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
    else:
        cfg = get_frps_dashboard_config()
        return jsonify({"success": True, "config": cfg})

@app.route("/api/frps/status")
def api_frps_status():
    import urllib.request
    import base64
    
    cfg = get_frps_dashboard_config()
    if not cfg.get("dash_enabled", False):
        return jsonify({"success": False, "enabled": False, "error": "服务端 Dashboard 对接未启用"})

    addr = cfg.get("dash_addr")
    port = cfg.get("dash_port", 7500)
    user = cfg.get("dash_user", "")
    password = cfg.get("dash_password", "")

    if not addr:
        return jsonify({"success": False, "enabled": True, "error": "服务端 Dashboard 地址未设置"})

    url = f"http://{addr}:{port}/api/serverinfo"
    req = urllib.request.Request(url)
    auth_bytes = None
    if user or password:
        auth_str = f"{user}:{password}"
        auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", f"Basic {auth_bytes}")

    try:
        with urllib.request.urlopen(req, timeout=3.0) as response:
            if response.status == 200:
                server_info = json.loads(response.read().decode("utf-8"))
                
                # 尝试进一步拉取各类代理的具体分布及状态
                proxy_details = {}
                for ptype in ["tcp", "udp", "http", "https", "stcp", "xtcp"]:
                    try:
                        purl = f"http://{addr}:{port}/api/proxy/{ptype}"
                        preq = urllib.request.Request(purl)
                        if auth_bytes:
                            preq.add_header("Authorization", f"Basic {auth_bytes}")
                        with urllib.request.urlopen(preq, timeout=1.5) as presp:
                            if presp.status == 200:
                                pdata = json.loads(presp.read().decode("utf-8"))
                                proxy_details[ptype] = pdata.get("proxies", [])
                    except Exception:
                        pass

                return jsonify({
                    "success": True,
                    "enabled": True,
                    "server_info": server_info,
                    "proxies": proxy_details
                })
            else:
                return jsonify({"success": False, "enabled": True, "error": f"服务端响应异常状态码: {response.status}"})
    except Exception as e:
        return jsonify({"success": False, "enabled": True, "error": f"无法连接到服务端 Dashboard ({addr}:{port}): {str(e)}"})
@app.route("/api/frps/test", methods=["POST"])
def api_frps_test():
    import urllib.request
    import base64
    try:
        data = request.json or {}
        addr = data.get("dash_addr", "").strip()
        port = int(data.get("dash_port", 7500))
        user = data.get("dash_user", "").strip()
        password = data.get("dash_password", "").strip()

        if not addr:
            return jsonify({"success": False, "error": "服务端 IP / 域名不能为空"})

        url = f"http://{addr}:{port}/api/serverinfo"
        req = urllib.request.Request(url)
        if user or password:
            auth_str = f"{user}:{password}"
            auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            req.add_header("Authorization", f"Basic {auth_bytes}")

        with urllib.request.urlopen(req, timeout=3.0) as response:
            if response.status == 200:
                server_info = json.loads(response.read().decode("utf-8"))
                v = server_info.get("version", "未知")
                return jsonify({
                    "success": True,
                    "message": f"🎉 连接成功！FRPS 服务端版本: {v}",
                    "server_info": server_info
                })
            else:
                return jsonify({"success": False, "error": f"服务端响应异常状态码: {response.status}"})
    except Exception as e:
        return jsonify({"success": False, "error": f"无法连接到服务端 Dashboard: {str(e)}"})




@app.before_request
def check_auth():
    if request.endpoint in ['login', 'static'] or request.path.startswith('/static'):
        return
    creds = get_auth_credentials()
    if not creds.get("auth_enabled", True):
        return
    if not session.get('logged_in'):
        if request.path.startswith('/api/'):
            return jsonify({"success": False, "error": "Unauthorized"}), 401
        return redirect('/login')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("u")
        password = request.form.get("p")
        creds = get_auth_credentials()
        if username == creds["username"] and password == creds["password"]:
            session["logged_in"] = True
            return redirect("/")
        else:
            return render_template("login.html", error_msg="❌ 账号或密码错误")
    
    if session.get("logged_in"):
        return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/login")

@app.route("/api/auth/update", methods=["POST"])
def api_update_auth():
    try:
        data = request.json
        new_user = data.get("username", "").strip()
        new_pass = data.get("password", "").strip()
        auth_enabled = data.get("auth_enabled", True)
        
        if auth_enabled and (not new_user or not new_pass):
            return jsonify({"success": False, "error": "启用密码认证时，用户名或密码不能为空"}), 400
        
        creds = get_auth_credentials()
        updated_user = new_user if new_user else creds["username"]
        updated_pass = new_pass if new_pass else creds["password"]
        
        with open(AUTH_FILE, "w") as f:
            json.dump({"username": updated_user, "password": updated_pass, "auth_enabled": auth_enabled}, f)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/")
def index():
    r = subprocess.run(["sudo", "systemctl", "is-active", "frpc"], capture_output=True, text=True)
    running = r.stdout.strip() == "active"
    logs = subprocess.run(["journalctl", "-u", "frpc", "-n", "50", "--no-pager"], capture_output=True, text=True).stdout[:3000]
    cfg = read_config()
    proxies = read_proxies()
    
    sc = "running" if running else "stopped"
    st = "运行中" if running else "已停止"
    icon = "🟢" if running else "⚪️"
    btn = "<button type='button' onclick='controlService(\"stop\")' class='btn btn-danger' id='btnStop'>停止</button><button type='button' onclick='controlService(\"restart\")' class='btn btn-secondary' id='btnRestart'>重启</button>" if running else "<button type='button' onclick='controlService(\"start\")' class='btn btn-primary' id='btnStart'>启动</button>"
    
    proxy_rows = ""
    for i, p in enumerate(proxies):
        proxy_rows += f"""<div class="proxy-item" id="proxy-{i}">
<div class="proxy-icon">📡</div>
<div class="proxy-info">
<span class="proxy-name">{p['name']}</span>
<span class="proxy-detail">{p['localIP']}:{p['localPort']}<span class="arrow">→</span>{p['remotePort']}</span>
</div>
<div class="proxy-type">{p['type'].upper()}</div>
<div class="proxy-actions">
<button class="btn-icon" onclick="editProxy({i})">✏️</button>
<button class="btn-icon btn-delete" onclick="deleteProxy({i})">🗑️</button>
</div></div>"""
    
    if not proxies:
        proxy_rows = '<div class="empty-state"><div class="empty-icon">📭</div><div class="empty-text">暂无转发配置</div></div>'
    
    proxies_json = json.dumps(proxies)
    auth_creds = get_auth_credentials()
    auth_config_json = json.dumps({"auth_enabled": auth_creds.get("auth_enabled", True)})
    frps_config = get_frps_dashboard_config()
    frps_config_json = json.dumps(frps_config)
    
    return render_template("index.html", 
                           sc=sc, icon=icon, st=st, btn=btn, 
                           proxy_rows=proxy_rows, cfg=cfg, logs=logs, 
                           proxies_json=proxies_json, 
                           auth_config_json=auth_config_json,
                           frps_config_json=frps_config_json)


@app.route("/api/status")
def api_status():
    running = False
    # Check 1: systemctl
    try:
        r = subprocess.run(["sudo", "systemctl", "is-active", "frpc"], capture_output=True, text=True)
        if r.stdout.strip() == "active":
            running = True
    except Exception:
        pass
    
    # Check 2: process check if systemctl returns False (e.g. started via nohup)
    if not running:
        try:
            p = subprocess.run(["pgrep", "-f", "frpc"], capture_output=True, text=True)
            if p.returncode == 0 and p.stdout.strip():
                running = True
        except Exception:
            pass

    # Check 3: webServer API check as fallback
    if not running:
        addr, port, user, password = get_webserver_info()
        try:
            import urllib.request
            import base64
            url = f"http://{addr}:{port}/api/status"
            req = urllib.request.Request(url)
            auth_str = f"{user}:{password}"
            auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            req.add_header("Authorization", f"Basic {auth_bytes}")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    running = True
        except Exception:
            pass

    return jsonify({"running": running})

@app.route("/api/logs")
def api_logs():
    logs = subprocess.run(["journalctl", "-u", "frpc", "-n", "50", "--no-pager"], capture_output=True, text=True).stdout[:3000]
    return jsonify({"logs": logs})

@app.route("/api/proxies")
def api_proxies():
    proxies = read_proxies()
    return jsonify({"proxies": proxies})

def read_config():
    try:
        with open(CFG) as f: c = f.read()
        # 支持新旧两种格式
        tk = re.search(r'auth\.token = "([^"]+)"', c) or re.search(r'\[auth\][^\[]*token = "([^"]+)"', c, re.DOTALL)
        return {"sa": re.search(r'serverAddr = "([^"]+)"', c).group(1) or "your-server-ip",
                "sp": re.search(r"serverPort = (\d+)", c).group(1) or "5443",
                "tk": tk.group(1) if tk else "",
                "li": "10.0.0.2", "lp": "80", "rp": "8080"}
    except:
        return {"sa": "your-server-ip", "sp": "5443", "tk": "", "li": "10.0.0.2", "lp": "80", "rp": "8080"}

def read_proxies():
    proxies = []
    try:
        with open(CFG) as f: c = f.read()
        proxy_blocks = re.findall(r'\[\[proxies\]\]\n(.*?)(?=\[\[proxies\]\]|\Z)', c, re.DOTALL)
        for block in proxy_blocks:
            name = re.search(r'name = "([^"]+)"', block)
            ptype = re.search(r'type = "([^"]+)"', block)
            lip = re.search(r'localIP = "([^"]+)"', block)
            lport = re.search(r'localPort = (\d+)', block)
            rport = re.search(r'remotePort = (\d+)', block)
            custom_domain = re.search(r'customDomains = \["([^"]+)"\]', block)
            http_user = re.search(r'httpUser = "([^"]+)"', block)
            http_pass = re.search(r'httpPassword = "([^"]+)"', block)
            if name and ptype:
                proxies.append({
                    "name": name.group(1), "type": ptype.group(1),
                    "localIP": lip.group(1) if lip else "127.0.0.1",
                    "localPort": lport.group(1) if lport else "80",
                    "remotePort": rport.group(1) if rport else "",
                    "customDomain": custom_domain.group(1) if custom_domain else "",
                    "httpUser": http_user.group(1) if http_user else "",
                    "httpPassword": http_pass.group(1) if http_pass else ""
                })
    except Exception as e:
        print(f"Error: {e}")
    return proxies

def generate_config_content(proxies):
    c = ""
    if os.path.exists(CFG):
        try:
            with open(CFG) as f: c = f.read()
        except:
            pass
    sa_match = re.search(r'serverAddr = "([^"]+)"', c)
    sa = sa_match.group(1) if sa_match else "your-server-ip"
    sp_match = re.search(r"serverPort = (\d+)", c)
    sp = sp_match.group(1) if sp_match else "5443"
    tk = re.search(r'auth\.token = "([^"]+)"', c) or re.search(r'\[auth\][^\[]*token = "([^"]+)"', c, re.DOTALL)
    token = tk.group(1) if tk else ""
    cfg = f'serverAddr = "{sa}"\nserverPort = {sp}\n\n[auth]\ntoken = "{token}"\n\n[transport]\ntcpMux = true\n\n[log]\nlevel = "info"\nmaxDays = 3\n\n[webServer]\naddr = "127.0.0.1"\nport = 7400\nuser = "admin"\npassword = "admin"\n'
    for p in proxies:
        if p["type"] in ["http", "https"]:
            cfg += f'\n[[proxies]]\nname = "{p["name"]}"\ntype = "{p["type"]}"\nlocalIP = "{p["localIP"]}"\nlocalPort = {p["localPort"]}\n'
            if p.get("httpUser") and p.get("httpPassword"):
                cfg += f'httpUser = "{p["httpUser"]}"\nhttpPassword = "{p["httpPassword"]}"\n'
            cfg += f'customDomains = ["{p.get("customDomain", p["name"] + ".example.com")}"]\n'
        else:
            cfg += f'\n[[proxies]]\nname = "{p["name"]}"\ntype = "{p["type"]}"\nlocalIP = "{p["localIP"]}"\nlocalPort = {p["localPort"]}\nremotePort = {p["remotePort"]}\n'
    return cfg

def find_frpc_path():
    paths = ["/usr/local/frp/frpc", "/usr/local/bin/frpc", "/usr/bin/frpc"]
    for p in paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    try:
        r = subprocess.run(["which", "frpc"], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
    except:
        pass
    return None

def apply_config_and_restart(new_config_str):
    # 1. 静态语法 Dry Run 校验
    frpc_path = find_frpc_path()
    if frpc_path:
        temp_cfg = "/tmp/frpc_verify.toml"
        try:
            with open(temp_cfg, "w") as f:
                f.write(new_config_str)
            r = subprocess.run([frpc_path, "verify", "-c", temp_cfg], capture_output=True, text=True)
            if r.returncode != 0 and "unknown command" not in r.stderr:
                err = r.stderr.strip() or r.stdout.strip() or "静态配置语法格式错误"
                return False, f"⚠️ 配置格式校验失败，已阻断应用：{err}"
        except Exception as e:
            pass
        finally:
            if os.path.exists(temp_cfg):
                try: os.remove(temp_cfg)
                except: pass

    # 2. 备份当前配置
    old_config_str = ""
    if os.path.exists(CFG):
        try:
            with open(CFG) as f: old_config_str = f.read()
        except:
            pass

    # 3. 写入新配置
    try:
        os.makedirs(os.path.dirname(CFG), exist_ok=True)
        with open(CFG, "w") as f:
            f.write(new_config_str)
    except Exception as e:
        return False, f"无法写入配置文件：{e}"

    # 4. 重启服务
    try:
        subprocess.run(["sudo", "systemctl", "restart", "frpc"], check=True, capture_output=True)
    except Exception as e:
        return False, f"无法重启 frpc 服务：{e}"

    # 5. 动态跟踪检测 3 秒
    import time
    for _ in range(6):
        time.sleep(0.5)
        r = subprocess.run(["sudo", "systemctl", "is-active", "frpc"], capture_output=True, text=True)
        if r.stdout.strip() != "active":
            # 获取崩溃日志
            logs_r = subprocess.run(["journalctl", "-u", "frpc", "-n", "10", "--no-pager"], capture_output=True, text=True)
            crash_logs = logs_r.stdout.strip() or "服务启动后在 3 秒内发生意外退出了"
            # 自动回滚
            if old_config_str:
                try:
                    with open(CFG, "w") as f: f.write(old_config_str)
                    subprocess.run(["sudo", "systemctl", "restart", "frpc"])
                except Exception as rollback_err:
                    crash_logs += f"\n(且配置自动还原失败：{rollback_err})"
            return False, f"🚨 服务启动失败，已自动回滚配置！崩溃原因：\n{crash_logs}"

    return True, None

def write_proxies(proxies):
    content = generate_config_content(proxies)
    with open(CFG, "w") as f: f.write(content)

@app.route("/api/proxy/save", methods=["POST"])
def api_save_proxy():
    try:
        data = request.json
        proxies = read_proxies()
        idx = data.get('index', -1)
        new_proxy = {
            "name": data['name'],
            "type": data['type'],
            "localIP": data['localIP'],
            "localPort": data['localPort'],
            "remotePort": data['remotePort'],
            "httpUser": data.get('httpUser', ''),
            "httpPassword": data.get('httpPassword', '')
        }
        if idx >= 0 and idx < len(proxies): proxies[idx] = new_proxy
        else: proxies.append(new_proxy)
        
        new_cfg_content = generate_config_content(proxies)
        success, err_msg = apply_config_and_restart(new_cfg_content)
        if not success:
            return jsonify({"success": False, "error": err_msg}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/proxy/delete", methods=["POST"])
def api_delete_proxy():
    try:
        data = request.json
        proxies = read_proxies()
        idx = data.get('index', -1)
        if idx >= 0 and idx < len(proxies):
            proxies.pop(idx)
            new_cfg_content = generate_config_content(proxies)
            success, err_msg = apply_config_and_restart(new_cfg_content)
            if not success:
                return jsonify({"success": False, "error": err_msg}), 400
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid index"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/save", methods=["POST"])
def save():
    sa = request.form.get("sa")
    sp = request.form.get("sp")
    tk = request.form.get("tk")
    proxies = read_proxies()
    cfg_content = f'serverAddr = "{sa}"\nserverPort = {sp}\n\n[auth]\ntoken = "{tk}"\n\n[transport]\ntcpMux = true\n\n[log]\nlevel = "info"\nmaxDays = 3\n\n[webServer]\naddr = "127.0.0.1"\nport = 7400\nuser = "admin"\npassword = "admin"\n'
    for p in proxies:
        if p["type"] in ["http", "https"]:
            cfg_content += f'\n[[proxies]]\nname = "{p["name"]}"\ntype = "{p["type"]}"\nlocalIP = "{p["localIP"]}"\nlocalPort = {p["localPort"]}\n'
            if p.get("httpUser") and p.get("httpPassword"):
                cfg_content += f'httpUser = "{p["httpUser"]}"\nhttpPassword = "{p["httpPassword"]}"\n'
            cfg_content += f'customDomains = ["{p.get("customDomain", p["name"] + ".example.com")}"]\n'
        else:
            cfg_content += f'\n[[proxies]]\nname = "{p["name"]}"\ntype = "{p["type"]}"\nlocalIP = "{p["localIP"]}"\nlocalPort = {p["localPort"]}\nremotePort = {p["remotePort"]}\n'
            
    success, err_msg = apply_config_and_restart(cfg_content)
    if not success:
        err_html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>FRP Manager - Error</title>
<style>
body { font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif; background:#F2F2F7; padding:40px 20px; text-align:center; }
.card { background:#fff; max-width:500px; margin:0 auto; padding:30px; border-radius:14px; box-shadow:0 8px 30px rgba(0,0,0,0.08); text-align:left; }
h2 { color:#FF3B30; margin-bottom:12px; }
pre { background:#F2F2F7; padding:12px; border-radius:8px; font-family:monospace; font-size:12px; white-space:pre-wrap; }
.btn { display:inline-block; margin-top:20px; background:#007AFF; color:#fff; text-decoration:none; padding:10px 20px; border-radius:8px; font-weight:600; }
</style></head>
<body><div class="card">
<h2>🚨 配置更新失败，已自动恢复！</h2>
<p>应用主配置时，服务未能正常拉起。为了保障控制面板与代理服务的可用性，系统已自动回滚了配置文件。</p>
<hr style="margin:20px 0; border:0; border-top:1px solid rgba(60,60,67,0.12)">
<p><strong>详细排错日志：</strong></p>
<pre>ERROR_MSG_PLACEHOLDER</pre>
<a href="/" class="btn">返回主页面</a>
</div></body></html>"""
        return err_html.replace("ERROR_MSG_PLACEHOLDER", str(err_msg))
    return redirect("/")

@app.route("/ctrl", methods=["POST"])
@app.route("/api/ctrl", methods=["POST"])
def ctrl():
    action = None
    if request.is_json:
        data = request.get_json(silent=True) or {}
        action = data.get("a") or data.get("action")
    else:
        action = request.form.get("a") or request.form.get("action")

    if action not in ["start", "stop", "restart"]:
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return jsonify({"success": False, "error": "无效的控制指令"}), 400
        return redirect("/")

    res = subprocess.run(["sudo", "systemctl", action, "frpc"], capture_output=True, text=True)
    
    action_text_map = {"start": "启动", "stop": "停止", "restart": "重启"}
    action_name = action_text_map.get(action, action)
    
    if res.returncode == 0:
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return jsonify({"success": True, "action": action, "message": f"服务{action_name}成功"})
        return redirect("/")
    else:
        err_msg = res.stderr.strip() or f"服务{action_name}失败"
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return jsonify({"success": False, "error": err_msg}), 500
        return redirect("/")

def is_safe_filename(filename):
    if not re.match(r'^[a-zA-Z0-9_\-\.]+\.toml$', filename):
        return False
    if ".." in filename or "/" in filename or "\\" in filename:
        return False
    return True

@app.route("/api/configs")
def api_configs():
    configs = []
    cfg_dir = os.path.dirname(CFG)
    if not os.path.exists(cfg_dir):
        os.makedirs(cfg_dir, exist_ok=True)
        
    files = [f for f in os.listdir(cfg_dir) if f.endswith(".toml") and f != "frpc.toml"]
    # 额外过滤不安全的文件名，防止垃圾或恶意注入显现
    files = [f for f in files if is_safe_filename(f)]
    if not files:
        default_path = os.path.join(cfg_dir, "default.toml")
        if not os.path.exists(default_path):
            default_content = 'serverAddr = "your-server-ip"\nserverPort = 5443\n\n[auth]\ntoken = ""\n\n[transport]\ntcpMux = true\n\n[log]\nlevel = "info"\nmaxDays = 3\n'
            try:
                with open(default_path, "w") as f: f.write(default_content)
                files.append("default.toml")
            except: pass
        else:
            files.append("default.toml")
        
    if not os.path.exists(CFG) and not os.path.islink(CFG):
        try:
            os.symlink(os.path.join(cfg_dir, files[0]), CFG)
        except: pass
        
    active_file = "frpc.toml"
    if os.path.islink(CFG):
        try:
            active_file = os.path.basename(os.readlink(CFG))
        except: pass
        
    return jsonify({"configs": sorted(files), "active": active_file})

@app.route("/api/config/switch", methods=["POST"])
def api_config_switch():
    try:
        data = request.json
        target_file = data.get("file", "").strip()
        if not is_safe_filename(target_file):
            return jsonify({"success": False, "error": "非法的配置文件名称"}), 400
            
        cfg_dir = os.path.dirname(CFG)
        target_path = os.path.join(cfg_dir, target_file)
        
        if not target_file or not os.path.exists(target_path) or target_file == "frpc.toml":
            return jsonify({"success": False, "error": "目标配置文件无效"}), 400
            
        if os.path.exists(CFG) or os.path.islink(CFG):
            try: os.remove(CFG)
            except Exception as e: return jsonify({"success": False, "error": f"无法清理旧软链接: {e}"}), 500
            
        try:
            os.symlink(target_path, CFG)
        except Exception as e:
            return jsonify({"success": False, "error": f"创建软链接失败: {e}"}), 500
            
        with open(CFG) as f: content = f.read()
        success, err_msg = apply_config_and_restart(content)
        if not success:
            return jsonify({"success": False, "error": err_msg}), 400
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/config/create", methods=["POST"])
def api_config_create():
    try:
        data = request.json
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"success": False, "error": "配置文件名称不能为空"}), 400
        if not name.endswith(".toml"):
            name += ".toml"
        if name == "frpc.toml":
            return jsonify({"success": False, "error": "不能创建与系统软链接同名的配置文件"}), 400
        if not is_safe_filename(name):
            return jsonify({"success": False, "error": "非法的配置文件名称"}), 400
            
        cfg_dir = os.path.dirname(CFG)
        new_path = os.path.join(cfg_dir, name)
        if os.path.exists(new_path):
            return jsonify({"success": False, "error": "同名配置文件已存在"}), 400
            
        default_content = 'serverAddr = "your-server-ip"\nserverPort = 5443\n\n[auth]\ntoken = ""\n\n[transport]\ntcpMux = true\n\n[log]\nlevel = "info"\nmaxDays = 3\n'
        with open(new_path, "w") as f:
            f.write(default_content)
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=False)
