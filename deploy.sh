#!/bin/bash

# FRP Web Manager v1.2.0 - 一键部署脚本
# 功能：自动检测硬件平台 + 下载对应 frpc + 交互式配置
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

echo ""
echo "📦 安装依赖..."
apt update
apt install -y python3-pip git python3-flask

# 检测硬件平台
echo ""
echo "🔍 检测硬件平台..."
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        FRP_ARCH="amd64"
        echo "✅ 检测到 AMD64 架构 (x86_64) - Intel/AMD 桌面/服务器"
        ;;
    aarch64|arm64)
        FRP_ARCH="arm64"
        echo "✅ 检测到 ARM64 架构 ($ARCH) - 树莓派 4/ARM 服务器/Mac M1/M2"
        ;;
    armv7l)
        FRP_ARCH="arm"
        echo "✅ 检测到 ARM 架构 (armv7l) - 树莓派 3/旧款 ARM 设备"
        ;;
    *)
        echo "❌ 不支持的架构：$ARCH"
        exit 1
        ;;
esac

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

# 下载并部署 frpc 二进制
echo ""
echo "📦 下载并部署 frpc 二进制..."
FRP_VERSION="0.61.1"
FRP_FILE="frp_${FRP_VERSION}_linux-${FRP_ARCH}.tar.gz"
FRP_URL="https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/${FRP_FILE}"
FRP_DIR="/usr/local/frp"

echo "📥 下载 frp ${FRP_VERSION} (linux-${FRP_ARCH})..."
cd /tmp
curl -sL -o ${FRP_FILE} ${FRP_URL}
tar -xzf ${FRP_FILE}

echo "📁 安装到 ${FRP_DIR}..."
mkdir -p ${FRP_DIR}
cp frp_${FRP_VERSION}_linux-${FRP_ARCH}/frpc ${FRP_DIR}/
chmod +x ${FRP_DIR}/frpc

echo "⚙️ 配置 frpc 服务..."
cd $INSTALL_DIR
cp frpc.service /etc/systemd/system/ 2>/dev/null || echo "⚠️  frpc.service 已存在"

echo "✅ frpc ${FRP_VERSION} 安装完成"

echo ""
echo "⚙️ 配置服务..."
cp frp-web-manager.service /etc/systemd/system/
cp frpc.service /etc/systemd/system/ 2>/dev/null || echo "⚠️  frpc.service 已存在"

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
systemctl daemon-reload
systemctl enable $SERVICE_NAME $FRPC_SERVICE
systemctl restart $SERVICE_NAME $FRPC_SERVICE

echo ""
echo "========================================"
echo "✅ 部署完成！"
echo "========================================"
echo ""
echo "📊 服务状态:"
echo ""
systemctl status $SERVICE_NAME --no-pager | head -5
echo ""
systemctl status $FRPC_SERVICE --no-pager | head -5
echo ""

echo "🌐 访问地址：http://$(hostname -I | awk '{print $1}'):8081"
echo ""
echo "📝 日志查看：journalctl -u $SERVICE_NAME -f"
echo ""
echo "========================================"
