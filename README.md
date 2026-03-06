# FRP Web Manager

基于 Flask 的 FRP 客户端 Web 管理界面，采用 Apple 设计风格。

## ✨ 功能特性

- 📊 **服务状态监控** - 实时查看 frpc 运行状态
- 🎛️ **服务控制** - 启动/停止/重启 frpc 服务
- 📡 **代理配置管理** - 添加/编辑/删除转发配置
- ⚙️ **主配置编辑** - 修改 FRP 服务器连接参数
- 📋 **日志查看** - 实时查看 frpc 运行日志
- 🍎 **Apple 设计** - 符合 Apple Human Interface Guidelines 的 UI

## 🚀 快速部署

### 1. 安装依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3-pip docker.io

# 安装 Flask
pip3 install flask

# 或使用 Docker 部署
docker pull snowdreamtech/frpc:latest
```

### 2. 配置 FRP

```bash
sudo mkdir -p /usr/local/frp
sudo cp frpc.toml.example /usr/local/frp/frpc.toml

# 编辑配置文件
sudo nano /usr/local/frp/frpc.toml
```

### 3. 安装 Web Manager

```bash
# 创建目录
sudo mkdir -p /opt/frp-web-manager
cd /opt/frp-web-manager

# 复制文件
sudo cp app.py /opt/frp-web-manager/
sudo cp frp-web-manager.service /etc/systemd/system/

# 设置权限
sudo chmod +x app.py
```

### 4. 启动服务

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启用并启动服务
sudo systemctl enable frp-web-manager
sudo systemctl start frp-web-manager

# 检查状态
sudo systemctl status frp-web-manager
```

### 5. 配置 sudo 权限

```bash
# 允许无密码重启 frpc
echo "www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart frpc" | sudo tee /etc/sudoers.d/frp-web-manager
echo "www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop frpc" | sudo tee -a /etc/sudoers.d/frp-web-manager
echo "www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl start frpc" | sudo tee -a /etc/sudoers.d/frp-web-manager
echo "www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active frpc" | sudo tee -a /etc/sudoers.d/frp-web-manager
```

## 🔧 配置说明

### FRP 配置 (`frpc.toml`)

```toml
serverAddr = "你的 FRP 服务器地址"
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

### Web Manager 配置

- **端口**: 8081
- **访问地址**: `http://服务器 IP:8081`

## 📱 UI 特性

- Apple Human Interface Guidelines 设计
- 响应式布局，适配手机/平板/桌面
- 毛玻璃效果 (backdrop-filter)
- SF Pro 系统字体
- 流畅的动画过渡

## 🛠️ 开发

### 本地运行

```bash
python3 app.py
```

### 修改后部署

```bash
# 提交更改
git add .
git commit -m "描述你的更改"
git push

# 在目标服务器上拉取
cd /opt/frp-web-manager
sudo git pull
sudo systemctl restart frp-web-manager
```

## 📄 文件结构

```
frp-web-manager/
├── app.py                      # Flask 应用主程序
├── frp-web-manager.service     # systemd 服务配置
├── frpc.toml.example          # FRP 配置模板
├── README.md                   # 本文件
└── .gitignore                  # Git 忽略文件
```

## 🔐 安全建议

1. 修改默认端口 (8081)
2. 使用 HTTPS (通过 Nginx 反向代理)
3. 添加认证中间件
4. 限制访问 IP
5. 定期更新依赖

## 📝 更新日志

### v1.0.0 (2026-03-06)
- ✨ 初始版本
- 🍎 Apple 设计风格 UI
- 📡 代理配置 CRUD 操作
- 📊 服务状态监控
- 📋 实时日志查看
- 🐛 修复弹窗关闭问题
- ⚡ 优化 API 响应速度

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 支持

如有问题，请提交 Issue 或联系作者。
