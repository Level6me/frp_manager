#!/bin/bash

# FRP Web Manager 部署脚本 - 支持 Docker 和二进制两种模式
# 使用：sudo ./deploy.sh

set -e

echo "🚀 FRP Web Manager 部署脚本"
echo "=========================="

# 配置
INSTALL_DIR="/opt/frp-web-manager"
SERVICE_NAME="frp-web-manager"
FRPC_SERVICE="frpc"

# 检查是否 root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# 检测 frpc 安装方式
echo "🔍 检测 frpc 安装方式..."
if command -v docker &> /dev/null && sudo docker ps --format '{{.Image}}' | grep -q frpc; then
    FRPC_MODE="docker"
    echo "✅ 检测到 Docker 版 frpc"
elif [ -f "/usr/local/frp/frpc" ]; then
    FRPC_MODE="binary"
    echo "✅ 检测到二进制版 frpc"
else
    echo "⚠️  未检测到 frpc，将仅部署 Web Manager"
    FRPC_MODE="none"
fi

echo ""
echo "📦 安装依赖..."
apt update
apt install -y python3-pip git
pip3 install flask

echo ""
echo "📁 创建目录..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

echo ""
echo "📥 克隆代码..."
if [ -d ".git" ]; then
    git pull
else
    git clone http://gogs.abab.pw/claw/frp_manager.git .
fi

echo ""
echo "⚙️ 配置服务..."
cp frp-web-manager.service /etc/systemd/system/

# 如果是二进制模式，复制 frpc 服务文件
if [ "$FRPC_MODE" = "binary" ]; then
    echo "📋 复制 frpc 服务文件（二进制版）..."
    cp frpc.service /etc/systemd/system/ 2>/dev/null || echo "⚠️  frpc.service 已存在"
fi

echo ""
echo "🔧 配置 sudo 权限..."
cat > /etc/sudoers.d/frp-web-manager << EOF
# FRP Web Manager 权限
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart $FRPC_SERVICE
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop $FRPC_SERVICE
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start $FRPC_SERVICE
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active $FRPC_SERVICE
EOF
chmod 440 /etc/sudoers.d/frp-web-manager

echo ""
echo "🔄 重载 systemd..."
systemctl daemon-reload

echo ""
echo "▶️ 启动服务..."
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo ""
echo "========================================"
echo "✅ 部署完成！"
echo "========================================"
echo ""
echo "📊 服务状态:"
systemctl status $SERVICE_NAME --no-pager | head -5
echo ""

if [ "$FRPC_MODE" = "binary" ]; then
    echo "📊 frpc 状态:"
    systemctl status $FRPC_SERVICE --no-pager | head -5
    echo ""
fi

echo "🌐 访问地址：http://$(hostname -I | awk '{print $1}'):8081"
echo ""
echo "📝 日志查看：journalctl -u $SERVICE_NAME -f"
echo ""
echo "========================================"
