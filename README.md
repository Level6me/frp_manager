# FRP Web Manager v1.2.0

基于 Flask 的 FRP 客户端 Web 管理界面，采用 Apple 设计风格。

## ✨ 功能特性

- 📊 **服务状态监控** - 实时查看 frpc 运行状态
- 🎛️ **服务控制** - 启动/停止/重启 frpc 服务
- 📡 **代理配置管理** - 添加/编辑/删除转发配置
- ⚙️ **主配置编辑** - 修改 FRP 服务器连接参数
- 📋 **日志查看** - 实时查看 frpc 运行日志
- 🍎 **Apple 设计** - 符合 Apple Human Interface Guidelines 的 UI
- 🔧 **一键部署** - 自动检测硬件平台 + 安装 frpc

## 🚀 快速部署

### 方式一：一键部署（推荐）

```bash
# 克隆仓库
cd /opt
sudo git clone http://gogs.abab.pw/claw/frp_manager.git
cd frp_manager

# 运行一键部署脚本
sudo ./deploy.sh
```

脚本会自动完成：
- ✅ 检测硬件平台（amd64/arm64/arm）
- ✅ 下载对应架构的 frpc
- ✅ 安装 Python 依赖
- ✅ 配置 systemd 服务
- ✅ 启动所有服务

### 方式二：手动部署

```bash
# 1. 安装依赖
sudo apt update
sudo apt install -y python3-flask git

# 2. 克隆代码
sudo mkdir -p /opt/frp-web-manager
cd /opt/frp-web-manager
sudo git clone http://gogs.abab.pw/claw/frp_manager.git .

# 3. 配置服务
sudo cp frp-web-manager.service /etc/systemd/system/
sudo cp frpc.service /etc/systemd/system/

# 4. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable frp-web-manager frpc
sudo systemctl start frp-web-manager frpc

# 5. 检查状态
sudo systemctl status frp-web-manager
```

## 🔧 配置说明

### FRP 配置

编辑 `/usr/local/frp/frpc.toml`：

```toml
serverAddr = "你的 FRP 服务器地址"
serverPort = 5443
auth.token = "你的 Token"

[[proxies]]
name = "web-http"
type = "tcp"
localIP = "10.0.0.2"
localPort = 80
remotePort = 8080
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

### v1.2.0 (2026-03-09)
- 🔍 **硬件平台自动检测** - 支持 amd64/arm64/arm 架构
- 📦 **自动下载 frpc** - 根据架构下载对应版本 (0.61.1)
- 🚀 **一键部署脚本** - deploy.sh 包含所有步骤
- 🐛 **修复 Python 依赖安装** - 使用 apt 安装 python3-flask

### v1.1.0 (2026-03-07)
- 🔧 纯二进制部署（移除 Docker）
- ⚙️ 交互式配置向导
- 📝 完善文档（DEPLOY.md, QUICKSTART.md）

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
