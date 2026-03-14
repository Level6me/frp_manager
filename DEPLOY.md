# 部署指南

## 📦 首次部署到 Git

### 1. 在 Gogs 创建仓库

访问：http://gogs.abab.pw

1. 登录账号：`claw` / 密码：`claw123`
2. 点击右上角 **➕** → **新建仓库**
3. 填写：
   - **仓库名**: `frp-web-manager`
   - **描述**: FRP Web Manager - Apple Design UI
   - **可见性**: 公开/私有 自选
   - **不要勾选** "使用 README 初始化"
4. 点击 **创建仓库**

### 2. 推送代码

创建仓库后，在本地执行：

```bash
cd /Users/jiang/.openclaw/workspace/frp-web-manager

# 如果还没添加远程仓库
git remote add origin http://gogs.abab.pw/claw/frp_manager.git

# 推送代码
git push -u origin main
```

输入凭据：
- 用户名：`claw`
- 密码：`claw123`

### 3. 配置凭证存储（可选）

避免每次都输入密码：

```bash
# 方法 1: 使用凭证存储
git config --global credential.helper store

# 然后推送一次，之后会自动保存凭据

# 方法 2: 使用 SSH（推荐）
# 在 Gogs 设置中添加 SSH 公钥，然后：
git remote set-url origin git@gogs.abab.pw:claw/frp_manager.git
```

---

## 🚀 部署到新服务器

### 快速部署（推荐）

```bash
# 在目标服务器上执行
cd /opt
sudo git clone http://gogs.abab.pw/claw/frp_manager.git
cd frp-web-manager
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

### 手动部署

```bash
# 1. 安装依赖
sudo apt update
sudo apt install -y python3-pip git
pip3 install flask

# 2. 克隆代码
cd /opt
sudo git clone http://gogs.abab.pw/claw/frp_manager.git
cd frp-web-manager

# 3. 配置 FRP
sudo mkdir -p /usr/local/frp
sudo cp frpc.toml.example /usr/local/frp/frpc.toml
sudo nano /usr/local/frp/frpc.toml  # 编辑配置

# 4. 安装服务
sudo cp app.py /opt/frp-web-manager/
sudo cp frp-web-manager.service /etc/systemd/system/

# 5. 配置 sudo 权限
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart frpc" | sudo tee /etc/sudoers.d/frp-web-manager
sudo chmod 440 /etc/sudoers.d/frp-web-manager

# 6. 启动服务
sudo systemctl daemon-reload
sudo systemctl enable frp-web-manager
sudo systemctl start frp-web-manager

# 7. 检查状态
sudo systemctl status frp-web-manager
```

---

## 🔄 更新流程

### 开发新功能

```bash
# 1. 在本地修改代码
cd /Users/jiang/.openclaw/workspace/frp-web-manager
nano app.py  # 或使用其他编辑器

# 2. 测试功能
python3 app.py  # 本地测试

# 3. 提交更改
git add .
git commit -m "feat: 添加新功能描述"

# 4. 推送到 Git
git push
```

### 在服务器上更新

```bash
# 在目标服务器上执行
cd /opt/frp-web-manager

# 1. 拉取最新代码
sudo git pull

# 2. 重启服务
sudo systemctl restart frp-web-manager

# 3. 查看日志
sudo journalctl -u frp-web-manager -f
```

---

## 📝 常用 Git 命令

```bash
# 查看状态
git status

# 查看提交历史
git log --oneline

# 查看远程仓库
git remote -v

# 拉取最新代码
git pull

# 推送更改
git push

# 创建新版本
git tag v1.0.1
git push origin v1.0.1
```

---

## 🔐 安全建议

### 1. 使用 HTTPS 认证

```bash
# 配置凭证存储
git config --global credential.helper store
```

### 2. 或使用 SSH（推荐）

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your@email.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 在 Gogs 设置 → SSH Keys 中添加公钥

# 修改远程仓库 URL
git remote set-url origin git@gogs.abab.pw:claw/frp_manager.git
```

### 3. 保护敏感信息

- ❌ 不要在代码中硬编码密码
- ✅ 使用配置文件或环境变量
- ✅ 在 `.gitignore` 中排除敏感文件

---

## 📊 项目结构

```
frp-web-manager/
├── app.py                      # Flask 应用（核心功能）
├── frp-web-manager.service     # systemd 服务配置
├── frpc.toml.example          # FRP 配置模板
├── deploy.sh                   # 自动部署脚本
├── README.md                   # 项目说明
├── DEPLOY.md                   # 部署指南（本文件）
└── .gitignore                  # Git 忽略文件
```

---

## 🆘 故障排除

### 问题 1: 推送失败 - 401 Unauthorized

**解决**: 检查用户名密码是否正确，或在 Gogs 设置中重置密码。

### 问题 2: 推送失败 - 404 Not Found

**解决**: 仓库不存在，请先在 Gogs 上创建仓库。

### 问题 3: 服务无法启动

```bash
# 查看日志
sudo journalctl -u frp-web-manager -f

# 检查端口占用
sudo lsof -i :8081

# 检查 Python 依赖
pip3 list | grep flask
```

### 问题 4: frpc 无法重启

```bash
# 检查 sudo 权限
sudo cat /etc/sudoers.d/frp-web-manager

# 测试权限
sudo systemctl restart frpc
```

---

## 📞 支持

如有问题，请提交 Issue 或联系作者。
