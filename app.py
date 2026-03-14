from flask import Flask, request, redirect, jsonify
import subprocess, re, json

app = Flask(__name__)
CFG = "/usr/local/frp/frpc.toml"

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
    btn = "<button type='submit' name='a' value='stop' class='btn btn-danger'>停止</button><button type='submit' name='a' value='restart' class='btn btn-secondary'>重启</button>" if running else "<button type='submit' name='a' value='start' class='btn btn-primary'>启动</button>"
    
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
    
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>FRP Manager</title>
<style>
:root {{
    --apple-blue: #007AFF;
    --apple-green: #34C759;
    --apple-red: #FF3B30;
    --apple-orange: #FF9500;
    --apple-gray: #8E8E93;
    --apple-light-gray: #F2F2F7;
    --apple-card: #FFFFFF;
    --apple-separator: rgba(60,60,67,0.12);
    --apple-bg: #F2F2F7;
    --apple-text: #1C1C1E;
    --apple-text-secondary: #8E8E93;
}}
* {{ margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }}
body {{
    font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;
    background:var(--apple-bg);
    color:var(--apple-text);
    line-height:1.47;
    letter-spacing:-0.022em;
    padding:0;
}}
.container {{ max-width:680px; margin:0 auto; padding-bottom:40px; }}

/* Header */
.header {{
    background:rgba(255,255,255,0.8);
    backdrop-filter:saturate(180%) blur(20px);
    -webkit-backdrop-filter:saturate(180%) blur(20px);
    padding:16px 20px;
    position:sticky;
    top:0;
    z-index:100;
    border-bottom:1px solid var(--apple-separator);
    display:flex;
    justify-content:space-between;
    align-items:center;
}}
.header h1 {{ font-size:28px; font-weight:700; letter-spacing:0.004em; }}
.refresh-btn {{
    background:var(--apple-light-gray);
    border:none;
    width:36px;
    height:36px;
    border-radius:10px;
    font-size:18px;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    transition:all 0.2s ease;
}}
.refresh-btn:hover {{ background:#E5E5EA; }}
.refresh-btn:active {{ transform:scale(0.92); }}
.refresh-btn.spinning {{ animation:spin 1s linear infinite; }}
@keyframes spin {{ 100% {{ transform:rotate(360deg); }} }}

/* Cards */
.card {{
    background:var(--apple-card);
    margin:20px 16px;
    border-radius:14px;
    overflow:hidden;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
}}
.card-header {{
    padding:16px 16px 12px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}}
.card-title {{ font-size:13px; font-weight:600; color:var(--apple-text-secondary); text-transform:uppercase; letter-spacing:0.06em; }}

/* Status */
.status-section {{ padding:16px; display:flex; align-items:center; justify-content:space-between; }}
.status-badge {{
    display:flex;
    align-items:center;
    gap:8px;
    padding:8px 14px;
    border-radius:20px;
    font-size:15px;
    font-weight:500;
}}
.status-badge.running {{ background:rgba(52,199,89,0.12); color:var(--apple-green); }}
.status-badge.stopped {{ background:rgba(142,142,147,0.12); color:var(--apple-gray); }}
.btn-group {{ display:flex; gap:10px; }}

/* Buttons */
.btn {{
    padding:10px 18px;
    border-radius:10px;
    border:none;
    font-size:15px;
    font-weight:500;
    cursor:pointer;
    transition:all 0.2s ease;
}}
.btn:active {{ transform:scale(0.96); opacity:0.8; }}
.btn-primary {{ background:var(--apple-blue); color:#fff; }}
.btn-secondary {{ background:var(--apple-light-gray); color:var(--apple-text); }}
.btn-danger {{ background:var(--apple-red); color:#fff; }}
.btn-sm {{ padding:8px 14px; font-size:14px; border-radius:8px; }}

/* Proxy List */
.proxy-list {{ padding:0; }}
.proxy-item {{
    display:flex;
    align-items:center;
    gap:12px;
    padding:14px 16px;
    background:var(--apple-card);
    border-bottom:1px solid var(--apple-separator);
    transition:background 0.15s ease;
}}
.proxy-item:last-child {{ border-bottom:none; }}
.proxy-item:active {{ background:var(--apple-light-gray); }}
.proxy-icon {{ font-size:22px; }}
.proxy-info {{ flex:1; min-width:0; }}
.proxy-name {{ font-size:16px; font-weight:500; display:block; }}
.proxy-detail {{ font-size:13px; color:var(--apple-text-secondary); display:flex; align-items:center; gap:6px; }}
.arrow {{ color:var(--apple-gray); }}
.proxy-type {{
    font-size:11px;
    font-weight:600;
    color:var(--apple-text-secondary);
    background:var(--apple-light-gray);
    padding:4px 10px;
    border-radius:6px;
    text-transform:uppercase;
}}
.proxy-actions {{ display:flex; gap:6px; }}
.btn-icon {{
    width:34px;
    height:34px;
    border-radius:8px;
    border:none;
    background:var(--apple-light-gray);
    font-size:16px;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    transition:all 0.15s ease;
}}
.btn-icon:active {{ transform:scale(0.92); }}
.btn-delete:active {{ background:rgba(255,59,48,0.15); }}

/* Empty State */
.empty-state {{ padding:48px 20px; text-align:center; }}
.empty-icon {{ font-size:48px; margin-bottom:12px; }}
.empty-text {{ color:var(--apple-text-secondary); font-size:15px; }}

/* Form */
.form-section {{ padding:16px; }}
.form-grid {{ display:grid; gap:16px; }}
.form-group {{ display:flex; flex-direction:column; gap:6px; }}
.form-group label {{ font-size:13px; color:var(--apple-text-secondary); font-weight:500; }}
.form-group input,.form-group select {{
    width:100%;
    padding:12px 14px;
    border:1px solid var(--apple-separator);
    border-radius:10px;
    font-size:16px;
    background:var(--apple-card);
    transition:all 0.2s ease;
    -webkit-appearance:none;
}}
.form-group input:focus,.form-group select:focus {{
    outline:none;
    border-color:var(--apple-blue);
    box-shadow:0 0 0 4px rgba(0,122,255,0.15);
}}

/* Logs */
.logs {{
    background:#F2F2F7;
    padding:14px;
    max-height:280px;
    overflow-y:auto;
    border-radius:10px;
    margin:16px;
}}
.logs pre {{
    font-family:"SF Mono",Monaco,Consolas,monospace;
    font-size:12px;
    color:#1C1C1E;
    line-height:1.5;
    white-space:pre-wrap;
}}

/* Modal */
.modal {{
    display:none;
    position:fixed;
    inset:0;
    background:rgba(0,0,0,0.4);
    backdrop-filter:saturate(180%) blur(10px);
    -webkit-backdrop-filter:saturate(180%) blur(10px);
    z-index:1000;
    justify-content:center;
    align-items:center;
    padding:20px;
}}
.modal.active {{ display:flex; }}
.modal-content {{
    background:var(--apple-card);
    border-radius:14px;
    width:100%;
    max-width:420px;
    max-height:85vh;
    overflow-y:auto;
    box-shadow:0 20px 40px rgba(0,0,0,0.2);
}}
.modal-header {{
    padding:18px 20px;
    border-bottom:1px solid var(--apple-separator);
    display:flex;
    justify-content:space-between;
    align-items:center;
}}
.modal-header h3 {{ font-size:17px; font-weight:600; }}
.close-btn {{ background:none; border:none; font-size:24px; cursor:pointer; color:var(--apple-text-secondary); padding:0; width:28px; height:28px; display:flex; align-items:center; justify-content:center; }}
.modal-body {{ padding:20px; }}

/* Toast */
.toast {{
    position:fixed;
    bottom:40px;
    left:50%;
    transform:translateX(-50%) translateY(100px);
    background:rgba(28,28,30,0.92);
    backdrop-filter:saturate(180%) blur(20px);
    color:#fff;
    padding:14px 24px;
    border-radius:30px;
    font-size:15px;
    font-weight:500;
    z-index:1001;
    display:none;
    transition:all 0.3s cubic-bezier(0.175,0.885,0.32,1.275);
}}
.toast.show {{ transform:translateX(-50%) translateY(0); }}
.toast.success {{ background:rgba(52,199,89,0.95); }}
.toast.error {{ background:rgba(255,59,48,0.95); }}

/* Add Button */
.add-btn {{
    background:var(--apple-blue);
    color:#fff;
    border:none;
    padding:8px 14px;
    border-radius:8px;
    font-size:14px;
    font-weight:500;
    cursor:pointer;
    display:flex;
    align-items:center;
    gap:4px;
}}
.add-btn:active {{ transform:scale(0.96); }}

/* Loading */
.loading {{ opacity:0.5; pointer-events:none; transition:opacity 0.3s; }}
</style></head>
<body>
<div class="header">
<h1>FRP Manager</h1>
<button class="refresh-btn" id="refreshBtn" onclick="refreshAll()" title="刷新">🔄</button>
</div>
<div class="container">

<div class="card" id="statusCard">
<div class="card-header"><span class="card-title">服务状态</span></div>
<div class="status-section">
<div class="status-badge {sc}" id="statusBadge"><span>{icon}</span><span id="statusText">{st}</span></div>
<div class="btn-group" id="btnGroup">
<form method="post" action="/ctrl" style="display:inline">{btn}</form>
</div>
</div>
</div>

<div class="card" id="proxyCard">
<div class="card-header">
<span class="card-title">转发配置</span>
<button class="add-btn" onclick="addProxy()">➕ 添加</button>
</div>
<div class="proxy-list" id="proxyList">{proxy_rows}</div>
</div>

<div class="card">
<div class="card-header"><span class="card-title">主配置</span></div>
<div class="form-section">
<form method="post" action="/save">
<div class="form-grid">
<div class="form-group"><label>服务器地址</label><input name="sa" value="{cfg['sa']}"></div>
<div class="form-group"><label>服务器端口</label><input name="sp" type="number" value="{cfg['sp']}"></div>
<div class="form-group"><label>Token</label><input name="tk" value="{cfg['tk']}"></div>
<div class="form-group"><label>本地 IP</label><input name="li" value="{cfg['li']}"></div>
<div class="form-group"><label>本地端口</label><input name="lp" type="number" value="{cfg['lp']}"></div>
<div class="form-group"><label>远程端口</label><input name="rp" type="number" value="{cfg['rp']}"></div>
</div>
<div style="margin-top:18px"><button type="submit" class="btn btn-primary btn-sm" style="width:100%">保存配置</button></div>
</form>
</div>
</div>

<div class="card" id="logsCard">
<div class="card-header"><span class="card-title">运行日志</span></div>
<div class="logs"><pre id="logsContent">{logs}</pre></div>
</div>

</div>

<!-- Modal -->
<div class="modal" id="proxyModal">
<div class="modal-content">
<div class="modal-header">
<h3 id="modalTitle">编辑代理</h3>
<button class="close-btn" onclick="closeModal()">×</button>
</div>
<div class="modal-body">
<form id="proxyForm" onsubmit="saveProxy(event)">
<input type="hidden" id="proxyIndex" value="-1">
<div class="form-grid">
<div class="form-group"><label>名称</label><input type="text" id="pName" required placeholder="如：web-http"></div>
<div class="form-group"><label>类型</label><select id="pType" onchange="toggleAuthFields()"><option value="tcp">TCP</option><option value="udp">UDP</option><option value="http">HTTP</option><option value="https">HTTPS</option></select></div>
<div class="form-group"><label>本地 IP</label><input type="text" id="pLocalIP" value="10.0.0.2" required></div>
<div class="form-group"><label>本地端口</label><input type="number" id="pLocalPort" required placeholder="如：80"></div>
<div class="form-group"><label>远程端口</label><input type="number" id="pRemotePort" required placeholder="如：8080"></div>
<div id="authFields" style="display:none;border-top:1px solid var(--apple-separator);padding-top:16px;margin-top:8px">
<div style="grid-column:1/-1;display:flex;align-items:center;gap:8px;margin-bottom:12px">
<span style="font-size:13px;font-weight:600;color:var(--apple-text-secondary)">🔐 HTTP/HTTPS 配置</span>
</div>
<div class="form-group"><label>绑定域名</label><input type="text" id="pCustomDomain" placeholder="如：web.example.com（留空自动生成）"></div>
<div class="form-group"><label>用户名</label><input type="text" id="pHttpUser" placeholder="留空则禁用认证"></div>
<div class="form-group"><label>密码</label><input type="text" id="pHttpPassword" placeholder="留空则禁用认证"></div>
</div>
</div>
<div style="margin-top:20px;display:flex;gap:10px">
<button type="submit" class="btn btn-primary" style="flex:1">保存</button>
<button type="button" class="btn btn-secondary" style="flex:1" onclick="closeModal()">取消</button>
</div>
</form>
</div>
</div>
</div>

<div class="toast" id="toast"></div>

<script>
const proxies = {proxies_json};
let refreshInterval = null;

// 页面加载完成后开始自动刷新
document.addEventListener('DOMContentLoaded', function() {{
    // 每 5 秒自动刷新状态和日志
    startAutoRefresh();
}});

function startAutoRefresh() {{
    refreshInterval = setInterval(() => {{
        refreshStatus();
        refreshLogs();
    }}, 5000);
}}

function stopAutoRefresh() {{
    if(refreshInterval) {{
        clearInterval(refreshInterval);
        refreshInterval = null;
    }}
}}

function refreshAll() {{
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('spinning');
    
    refreshStatus();
    refreshLogs();
    refreshProxies();
    
    setTimeout(() => {{
        btn.classList.remove('spinning');
        showToast('已刷新');
    }}, 1000);
}}

function refreshStatus() {{
    fetch('/api/status')
        .then(r => r.json())
        .then(d => {{
            const badge = document.getElementById('statusBadge');
            const text = document.getElementById('statusText');
            const btnGroup = document.getElementById('btnGroup');
            
            if(d.running) {{
                badge.className = 'status-badge running';
                badge.innerHTML = '<span>🟢</span><span>运行中</span>';
                btnGroup.innerHTML = '<form method="post" action="/ctrl" style="display:inline"><button type="submit" name="a" value="stop" class="btn btn-danger">停止</button><button type="submit" name="a" value="restart" class="btn btn-secondary">重启</button></form>';
            }} else {{
                badge.className = 'status-badge stopped';
                badge.innerHTML = '<span>⚪️</span><span>已停止</span>';
                btnGroup.innerHTML = '<form method="post" action="/ctrl" style="display:inline"><button type="submit" name="a" value="start" class="btn btn-primary">启动</button></form>';
            }}
        }})
        .catch(e => console.error('Refresh status error:', e));
}}

function refreshLogs() {{
    fetch('/api/logs')
        .then(r => r.json())
        .then(d => {{
            document.getElementById('logsContent').textContent = d.logs;
        }})
        .catch(e => console.error('Refresh logs error:', e));
}}

function refreshProxies() {{
    fetch('/api/proxies')
        .then(r => r.json())
        .then(d => {{
            const list = document.getElementById('proxyList');
            if(d.proxies.length === 0) {{
                list.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><div class="empty-text">暂无转发配置</div></div>';
            }} else {{
                list.innerHTML = d.proxies.map(function(p, i) {{
                    return '<div class="proxy-item" id="proxy-' + i + '">' +
                        '<div class="proxy-icon">📡</div>' +
                        '<div class="proxy-info">' +
                        '<span class="proxy-name">' + p.name + '</span>' +
                        '<span class="proxy-detail">' + p.localIP + ':' + p.localPort + '<span class="arrow">→</span>' + p.remotePort + '</span>' +
                        '</div>' +
                        '<div class="proxy-type">' + p.type.toUpperCase() + '</div>' +
                        '<div class="proxy-actions">' +
                        '<button class="btn-icon" onclick="editProxy(' + i + ')">✏️</button>' +
                        '<button class="btn-icon btn-delete" onclick="deleteProxy(' + i + ')">🗑️</button>' +
                        '</div></div>';
                }}).join('');
            }}
        }})
        .catch(e => console.error('Refresh proxies error:', e));
}}

function editProxy(idx) {{
    const p = proxies[idx];
    document.getElementById('proxyIndex').value = idx;
    document.getElementById('pName').value = p.name;
    document.getElementById('pType').value = p.type;
    document.getElementById('pLocalIP').value = p.localIP;
    document.getElementById('pLocalPort').value = p.localPort;
    document.getElementById('pRemotePort').value = p.remotePort || '';
    document.getElementById('pCustomDomain').value = p.customDomain || '';
    document.getElementById('pHttpUser').value = p.httpUser || '';
    document.getElementById('pHttpPassword').value = p.httpPassword || '';
    toggleAuthFields();
    document.getElementById('modalTitle').textContent = '编辑代理';
    document.getElementById('proxyModal').classList.add('active');
}}

function addProxy() {{
    document.getElementById('proxyIndex').value = -1;
    document.getElementById('pName').value = '';
    document.getElementById('pType').value = 'tcp';
    document.getElementById('pLocalIP').value = '10.0.0.2';
    document.getElementById('pLocalPort').value = '';
    document.getElementById('pRemotePort').value = '';
    document.getElementById('pCustomDomain').value = '';
    document.getElementById('pHttpUser').value = '';
    document.getElementById('pHttpPassword').value = '';
    toggleAuthFields();
    document.getElementById('modalTitle').textContent = '添加代理';
    document.getElementById('proxyModal').classList.add('active');
}}

function toggleAuthFields() {{
    const type = document.getElementById('pType').value;
    const authDiv = document.getElementById('authFields');
    if(type === 'http' || type === 'https') {{
        authDiv.style.display = 'block';
    }} else {{
        authDiv.style.display = 'none';
    }}
}}

function deleteProxy(idx) {{
    if(confirm('确定要删除这个代理配置吗？')) {{
        fetch('/api/proxy/delete', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{index: idx}})
        }}).then(r => r.json()).then(d => {{
            if(d.success) {{ showToast('已删除'); setTimeout(() => location.reload(), 1000); }}
            else {{ showToast(d.error, 'error'); }}
        }});
    }}
}}

function saveProxy(e) {{
    e.preventDefault();
    const data = {{
        index: parseInt(document.getElementById('proxyIndex').value),
        name: document.getElementById('pName').value,
        type: document.getElementById('pType').value,
        localIP: document.getElementById('pLocalIP').value,
        localPort: parseInt(document.getElementById('pLocalPort').value),
        remotePort: parseInt(document.getElementById('pRemotePort').value),
        customDomain: document.getElementById('pCustomDomain').value,
        httpUser: document.getElementById('pHttpUser').value,
        httpPassword: document.getElementById('pHttpPassword').value
    }};
    fetch('/api/proxy/save', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(data)
    }}).then(r => r.json()).then(d => {{
        if(d.success) {{ 
            showToast('保存成功！'); 
            closeModal();
            setTimeout(() => location.reload(), 1000); 
        }}
        else {{ showToast(d.error, 'error'); }}
    }});
}}

function closeModal() {{ document.getElementById('proxyModal').classList.remove('active'); }}

function showToast(msg, type) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show' + (type ? ' ' + type : '');
    setTimeout(() => {{ t.classList.remove('show'); }}, 2500);
}}

document.getElementById('proxyModal').addEventListener('click', function(e) {{
    if(e.target === this) closeModal();
}});
</script>
</body></html>"""
    return html

@app.route("/api/status")
def api_status():
    r = subprocess.run(["sudo", "systemctl", "is-active", "frpc"], capture_output=True, text=True)
    running = r.stdout.strip() == "active"
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
                    "localIP": lip.group(1) if lip else "10.0.0.2",
                    "localPort": lport.group(1) if lport else "80",
                    "remotePort": rport.group(1) if rport else "",
                    "customDomain": custom_domain.group(1) if custom_domain else "",
                    "httpUser": http_user.group(1) if http_user else "",
                    "httpPassword": http_pass.group(1) if http_pass else ""
                })
    except Exception as e:
        print(f"Error: {e}")
    return proxies

def write_proxies(proxies):
    with open(CFG) as f: c = f.read()
    sa = re.search(r'serverAddr = "([^"]+)"', c).group(1) or "your-server-ip"
    sp = re.search(r"serverPort = (\d+)", c).group(1) or "5443"
    tk = re.search(r'auth\.token = "([^"]+)"', c) or re.search(r'\[auth\][^\[]*token = "([^"]+)"', c, re.DOTALL)
    token = tk.group(1) if tk else ""
    # 新版 frpc 0.67.0+ 使用嵌套 TOML 格式
    cfg = f'serverAddr = "{sa}"\nserverPort = {sp}\n\n[auth]\ntoken = "{token}"\n\n[transport]\ntcpMux = true\n\n[log]\nlevel = "info"\nmaxDays = 3\n'
    for p in proxies:
        # HTTP/HTTPS 类型使用 customDomains 而不是 remotePort
        if p["type"] in ["http", "https"]:
            cfg += f'\n[[proxies]]\nname = "{p["name"]}"\ntype = "{p["type"]}"\nlocalIP = "{p["localIP"]}"\nlocalPort = {p["localPort"]}\n'
            if p.get("httpUser") and p.get("httpPassword"):
                cfg += f'httpUser = "{p["httpUser"]}"\nhttpPassword = "{p["httpPassword"]}"\n'
            cfg += f'customDomains = ["{p.get("customDomain", p["name"] + ".example.com")}"]\n'
        else:
            cfg += f'\n[[proxies]]\nname = "{p["name"]}"\ntype = "{p["type"]}"\nlocalIP = "{p["localIP"]}"\nlocalPort = {p["localPort"]}\nremotePort = {p["remotePort"]}\n'
    with open(CFG, "w") as f: f.write(cfg)

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
        write_proxies(proxies)
        subprocess.Popen(["sudo", "systemctl", "restart", "frpc"])
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
            write_proxies(proxies)
            subprocess.Popen(["sudo", "systemctl", "restart", "frpc"])
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid index"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/save", methods=["POST"])
def save():
    d = {"sa": request.form.get("sa"), "sp": request.form.get("sp"), "tk": request.form.get("tk"), "li": request.form.get("li"), "lp": request.form.get("lp"), "rp": request.form.get("rp")}
    proxies = read_proxies()
    write_proxies(proxies)
    subprocess.Popen(["sudo", "systemctl", "restart", "frpc"])
    return redirect("/")

@app.route("/ctrl", methods=["POST"])
def ctrl():
    subprocess.run(["sudo", "systemctl", request.form.get("a"), "frpc"])
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=False)
