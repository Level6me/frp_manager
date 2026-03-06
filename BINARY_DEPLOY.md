# 二进制文件部署指南

本指南适用于从 GitHub 下载 frp 二进制文件部署的场景（非 Docker）。

---

## 📦 环境要求

- **操作系统:** Linux (Ubuntu/Debian/CentOS/Raspberry Pi OS)
- **Python:** 3.8+
- **frp:** 从 GitHub 下载的二进制文件
- **网络:** 可访问外网（下载 frp）

---

## 🚀 快速部署

### 1. 下载并安装 frp

```bash
# 设置变量
FRP_VERSION="0.61.1"
ARCH="linux-arm64"  # 根据系统选择：linux-amd64, linux-arm, linux-arm64

# 下载 frp
cd /tmp
wget https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_${ARCH}.tar.gz

# 解压
tar -xzf frp_${FRP_VERSION}_${ARCH}.tar.gz
cd frp_${FRP_VERSION}_${ARCH}

# 移动到系统目录
sudo mkdir -p /usr/local/frp
sudo cp frpc /usr/local/frp/
sudo chmod +x /usr/local/frp/frpc

# 验证
/usr/local/frp/frpc --version
```

### 2. 配置 frpc

```bash
# 创建配置文件
sudo mkdir -p /usr/local/frp
sudo nano /usr/local/frp/frpc.toml
```

**配置示例：**

```toml
serverAddr = "120.55.251.145"
serverPort = 5443
auth.token = "你的 Token"
transport.tcpMux = true
log.level = "info"
log.maxDays = 3

[[proxies]]
name = "web-http"
type = "tcp"
localIP = "10.0.0.2"
localPort = 80
remotePort = 8080

[[proxies]]
name = "web-manager"
type = "tcp"
localIP = "10.0.0.2"
localPort = 8081
remotePort = 8081
```

### 3. 安装 systemd 服务

```bash
# 复制服务文件
sudo cp frpc.service /etc/systemd/system/

# 重载 systemd
sudo systemctl daemon-reload

# 启用并启动
sudo systemctl enable frpc
sudo systemctl start frpc

# 检查状态
sudo systemctl status frpc
```

### 4. 部署 Web Manager

```bash
# 创建目录
sudo mkdir -p /opt/frp-web-manager
cd /opt/frp-web-manager

# 克隆代码
sudo git clone http://gogs.abab.pw/claw/frp_manager.git .

# 安装依赖
sudo apt update
sudo apt install -y python3-pip
pip3 install flask

# 配置 sudo 权限（允许无密码重启 frpc）
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart frpc" | sudo tee /etc/sudoers.d/frp-web-manager
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop frpc" | sudo tee -a /etc/sudoers.d/frp-web-manager
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start frpc" | sudo tee -a /etc/sudoers.d/frp-web-manager
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active frpc" | sudo tee -a /etc/sudoers.d/frp-web-manager
sudo chmod 440 /etc/sudoers.d/frp-web-manager

# 启动 Web Manager
sudo systemctl daemon-reload
sudo systemctl enable frp-web-manager
sudo systemctl start frp-web-manager

# 检查状态
sudo systemctl status frp-web-manager
```

### 5. 验证访问

```bash
# 本地访问
curl http://localhost:8081

# 外网访问
# http://你的服务器IP:8081
```

---

## 🔧 手动部署步骤

### 完整手动流程

```bash
# 1. 下载 frp
FRP_VERSION="0.61.1"
ARCH="linux-amd64"  # 修改为你的架构
wget https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_${ARCH}.tar.gz

# 2. 解压安装
tar -xzf frp_${FRP_VERSION}_${ARCH}.tar.gz
cd frp_${FRP_VERSION}_${ARCH}
sudo mkdir -p /usr/local/frp
sudo cp frpc /usr/local/frp/
sudo chmod +x /usr/local/frp/frpc

# 3. 创建配置文件
sudo nano /usr/local/frp/frpc.toml

# 4. 创建 systemd 服务
sudo nano /etc/systemd/system/frpc.service
# 复制上面的服务文件内容

# 5. 启动 frpc
sudo systemctl daemon-reload
sudo systemctl enable frpc
sudo systemctl start frpc
sudo systemctl status frpc

# 6. 部署 Web Manager
cd /opt
sudo git clone http://gogs.abab.pw/claw/frp_manager.git
cd frp_manager
sudo pip3 install flask

# 7. 配置 sudo 权限
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart frpc" | sudo tee /etc/sudoers.d/frp-web-manager
sudo chmod 440 /etc/sudoers.d/frp-web-manager

# 8. 启动 Web Manager
python3 app.py  # 测试运行
# 或安装为服务
sudo cp frp-web-manager.service /etc/systemd/system/
sudo systemctl enable frp-web-manager
sudo systemctl start frp-web-manager
```

---

## 📊 Docker vs 二进制 对比

| 特性 | Docker 部署 | 二进制部署 |
|------|------------|-----------|
| **安装难度** | ⭐⭐⭐ 简单 | ⭐⭐⭐⭐ 中等 |
| **性能** | ⭐⭐⭐⭐ 好 | ⭐⭐⭐⭐⭐ 最佳 |
| **资源占用** | ⭐⭐⭐ 较高 | ⭐⭐⭐⭐⭐ 低 |
| **配置复杂度** | ⭐⭐⭐⭐ 需要注意网络 | ⭐⭐⭐ 直接 |
| **更新便利** | ⭐⭐⭐⭐⭐ 拉取镜像 | ⭐⭐⭐ 手动下载 |
| **适用场景** | 快速部署/测试 | 生产环境 |

---

## 🔍 系统架构检测

```bash
# 查看系统架构
uname -m

# 输出对应关系:
# x86_64 → linux-amd64
# aarch64 → linux-arm64
# armv7l → linux-arm
```

---

## 🛠️ 常见问题

### Q1: 下载速度慢

**解决：** 使用国内镜像

```bash
# 使用 Gitee 镜像
wget https://github.com.cnpmjs.org/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux-amd64.tar.gz
```

### Q2: frpc 无法启动

```bash
# 查看日志
sudo journalctl -u frpc -f

# 检查配置
/usr/local/frp/frpc -c /usr/local/frp/frpc.toml

# 检查端口占用
sudo lsof -i :5443
```

### Q3: Web Manager 无法重启 frpc

```bash
# 检查 sudo 权限
sudo cat /etc/sudoers.d/frp-web-manager

# 测试权限
sudo systemctl restart frpc

# 如果失败，重新配置
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart frpc" | sudo tee /etc/sudoers.d/frp-web-manager
```

### Q4: 防火墙阻止访问

```bash
# Ubuntu/Debian
sudo ufw allow 8081/tcp
sudo ufw allow 5443/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --permanent --add-port=5443/tcp
sudo firewall-cmd --reload
```

---

## 📝 文件结构

```
/usr/local/frp/
├── frpc              # frp 客户端二进制文件
└── frpc.toml         # frp 配置文件

/opt/frp-web-manager/
├── app.py            # Flask 应用
├── frp-web-manager.service  # systemd 服务
├── frpc.service      # frpc systemd 服务（二进制版）
├── deploy.sh         # 部署脚本
└── ...

/etc/systemd/system/
├── frpc.service      # frpc 服务
└── frp-web-manager.service  # Web Manager 服务
```

---

## 🔐 安全建议

1. **修改默认端口**
   ```bash
   # 在 app.py 中修改端口
   app.run(host="0.0.0.0", port=8081) → port=你的端口
   ```

2. **使用 HTTPS**
   ```bash
   # 使用 Nginx 反向代理
   sudo apt install nginx
   sudo nano /etc/nginx/sites-available/frp
   ```

3. **添加认证**
   ```python
   # 在 app.py 中添加简单的 HTTP Basic Auth
   from flask_httpauth import HTTPBasicAuth
   auth = HTTPBasicAuth()
   ```

4. **限制访问 IP**
   ```bash
   # 使用防火墙
   sudo ufw allow from 你的IP to any port 8081
   ```

---

## 📞 支持

如有问题，请提交 Issue 或联系作者。

**仓库地址：** http://gogs.abab.pw/claw/frp_manager.git
