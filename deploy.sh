#!/bin/bash

# FRP Web Manager 部署脚本
# 使用：sudo ./deploy.sh

set -e

echo "🚀 FRP Web Manager 部署脚本"
echo "=========================="

# 配置
INSTALL_DIR="/opt/frp-web-manager"
SERVICE_NAME="frp-web-manager"

# 检查是否 root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

echo "📦 安装依赖..."
apt update
apt install -y python3-pip git
pip3 install flask

echo "📁 创建目录..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

echo "📥 克隆代码..."
if [ -d ".git" ]; then
    git pull
else
    git clone http://gogs.abab.pw/claw/frp-web-manager.git .
fi

echo "⚙️ 配置服务..."
cp frp-web-manager.service /etc/systemd/system/

echo "🔧 配置 sudo 权限..."
cat > /etc/sudoers.d/frp-web-manager << 'EOF'
# FRP Web Manager 权限
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart frpc
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop frpc
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start frpc
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active frpc
EOF
chmod 440 /etc/sudoers.d/frp-web-manager

echo "🔄 重载 systemd..."
systemctl daemon-reload

echo "▶️ 启动服务..."
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo ""
echo "✅ 部署完成！"
echo ""
echo "📊 服务状态:"
systemctl status $SERVICE_NAME --no-pager | head -5
echo ""
echo "🌐 访问地址：http://$(hostname -I | awk '{print $1}'):8081"
echo ""
echo "📝 日志查看：journalctl -u $SERVICE_NAME -f"
