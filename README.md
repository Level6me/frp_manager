# FRP Web Manager v1.3.2

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
- ✅ 选择 frpc 版本（最新版/最近 5 版/自定义）
- ✅ 配置 FRP 服务器连接（地址/端口/Token）
- ✅ 配置本地服务（IP/Web 端口/远程端口）
- ✅ 配置确认（显示完整清单，用户确认后才安装）
- ✅ 下载对应架构的 frpc
- ✅ 安装 Python 依赖
- ✅ 配置 systemd 服务
- ✅ 启动所有服务
- ✅ 显示完成状态（服务运行状态 + 访问地址）

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
serverPort = 你的服务器端口
auth.token = "你的 Token"

[[proxies]]
name = "web-http"
type = "tcp"
localIP = "你的本地 IP"
localPort = 你的本地端口
remotePort = 你的远程端口
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

### v1.3.2 (2026-03-14)
- 🎨 **美化安装界面** - 彩色输出 + 边框 + 图标
- ✨ **视觉层次优化** - 分阶段标题框 + 配置确认框 + 完成状态框
- 📊 **服务状态显示** - 完成时显示 Web Manager 和 frpc 运行状态
- › **统一输入提示符** - 更友好的交互体验

### v1.3.1 (2026-03-14)
- 🔄 **重构部署流程** - 先配置后安装，避免安装到一半发现问题
- 📋 **配置确认环节** - 显示完整配置清单，用户确认后才开始安装
- 📥 **代码仓库自动克隆/更新** - 智能判断是否需要 git clone 或 pull
- 📝 **优化输出格式** - 分阶段显示进度，清晰明了

### v1.3.0 (2026-03-14)
- 📦 **新增 frpc 版本选择功能** - 部署时可选择版本
  - 选项 1：默认最新版本 (v0.61.1)
  - 选项 2：最新的五个版本 (v0.61.1 ~ v0.58.0)
  - 选项 3：自定义版本（手动输入任意版本号）
- ⚠️ **增强错误处理** - 下载/解压失败时给出明确提示
- 📝 **更新文档** - README 和 deploy.sh 同步更新

### v1.2.2 (2026-03-09)
- 🗑️ **移除自动克隆代码步骤** - deploy.sh 不再执行 git clone/pull，需手动克隆

### v1.2.1 (2026-03-09)
- 🔧 **修复配置文件权限问题** - deploy.sh 自动设置 frpc.toml 可写权限
- 📦 **升级 frpc 到 v0.67.0** - 支持最新版本
- ✅ **解决 Web Manager 无法保存配置的问题** - chown 设置正确所有者

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
