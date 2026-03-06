# 快速开始 - 推送到 Git

## ⚡ 3 步完成推送

### 第 1 步：在 Gogs 创建仓库

打开浏览器访问：http://gogs.abab.pw

1. 登录账号：`claw`
2. 密码：`claw123`
3. 点击 **➕ 新建仓库**
4. 仓库名：`frp-web-manager`
5. **不要勾选** "使用 README 初始化"
6. 点击 **创建**

### 第 2 步：推送代码

在终端执行：

```bash
cd /Users/jiang/.openclaw/workspace/frp-web-manager
git remote add origin http://gogs.abab.pw/claw/frp-web-manager.git
git push -u origin main
```

输入密码：`claw123`

### 第 3 步：验证

访问：http://gogs.abab.pw/claw/frp-web-manager

应该能看到所有代码文件！

---

## 🔄 日后更新

```bash
cd /Users/jiang/.openclaw/workspace/frp-web-manager

# 修改代码后
git add .
git commit -m "描述你的更改"
git push

# 或使用快速脚本
./push.sh "描述你的更改"
```

---

## 📥 部署到其他服务器

```bash
# 在目标服务器上
cd /opt
sudo git clone http://gogs.abab.pw/claw/frp-web-manager.git
cd frp-web-manager
sudo ./deploy.sh
```

---

## ✅ 完成！

现在你的代码已经安全保存在 Git 服务器上了！🎉
