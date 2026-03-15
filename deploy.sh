#!/bin/bash

# FRP Web Manager v1.4.3 - 一键部署脚本
# 功能：美化安装界面 + 先配置后安装
# 使用：sudo ./deploy.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# 配置
INSTALL_DIR="/opt/frp-web-manager"
SERVICE_NAME="frp-web-manager"
FRPC_SERVICE="frpc"
FRP_DIR="/usr/local/frp"

# 打印横幅
print_banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}          ${BOLD}🚀 FRP Web Manager 一键部署脚本${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                    ${YELLOW}v1.3.2${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 打印阶段标题
print_stage() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${BOLD}$1${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 打印步骤
print_step() {
    echo -e "${GREEN}✓${NC} $1"
}

# 打印警告
print_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 打印错误
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 打印成功
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# 输入提示
input_prompt() {
    echo -ne "${CYAN}›${NC} $1 "
}

# 检查是否 root
if [ "$EUID" -ne 0 ]; then 
    print_error "请使用 sudo 运行此脚本"
    exit 1
fi

# 打印横幅
print_banner

# ==================== 第一阶段：配置 ====================
print_stage "📝 第一阶段：配置收集"

# 检测硬件平台
echo -e "${YELLOW}🔍${NC} 检测硬件平台..."
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        FRP_ARCH="amd64"
        print_success "AMD64 架构 (x86_64) - Intel/AMD 桌面/服务器"
        ;;
    aarch64|arm64)
        FRP_ARCH="arm64"
        print_success "ARM64 架构 ($ARCH) - 树莓派 4/ARM 服务器/Mac M1/M2"
        ;;
    armv7l)
        FRP_ARCH="arm"
        print_success "ARM 架构 (armv7l) - 树莓派 3/旧款 ARM 设备"
        ;;
    *)
        print_error "不支持的架构：$ARCH"
        exit 1
        ;;
esac

# 选择 frpc 版本
echo ""
echo -e "${BOLD}📦 选择 frpc 版本：${NC}"
echo -e "   ${GREEN}1)${NC} 默认最新版本 (v0.61.1)"
echo -e "   ${GREEN}2)${NC} 最新的五个版本 (v0.61.1 ~ v0.58.0)"
echo -e "   ${GREEN}3)${NC} 自定义版本"
echo ""
input_prompt "请输入选项 (1/2/3，默认 1): "
read VERSION_CHOICE

case $VERSION_CHOICE in
    2)
        echo ""
        echo -e "${BOLD}可选择的版本：${NC}"
        echo -e "   ${GREEN}1)${NC} v0.61.1 (最新)"
        echo -e "   ${GREEN}2)${NC} v0.61.0"
        echo -e "   ${GREEN}3)${NC} v0.60.0"
        echo -e "   ${GREEN}4)${NC} v0.59.0"
        echo -e "   ${GREEN}5)${NC} v0.58.0"
        echo ""
        input_prompt "请选择版本 (1-5，默认 1): "
        read VERSION_SELECT
        case $VERSION_SELECT in
            2) FRP_VERSION="0.61.0" ;;
            3) FRP_VERSION="0.60.0" ;;
            4) FRP_VERSION="0.59.0" ;;
            5) FRP_VERSION="0.58.0" ;;
            *) FRP_VERSION="0.61.1" ;;
        esac
        ;;
    3)
        echo ""
        input_prompt "请输入自定义版本号 (如：0.54.0): "
        read CUSTOM_VERSION
        FRP_VERSION="$CUSTOM_VERSION"
        ;;
    *)
        FRP_VERSION="0.61.1"
        ;;
esac

# FRP 服务器配置
echo ""
echo -e "${BOLD}🌐 配置 FRP 服务器连接：${NC}"
input_prompt "FRP 服务器地址 [your-server-ip]: "
read FRP_SERVER
FRP_SERVER=${FRP_SERVER:-"your-server-ip"}

input_prompt "FRP 服务器端口 [5443]: "
read FRP_PORT
FRP_PORT=${FRP_PORT:-"5443"}

input_prompt "Token [your-token]: "
read FRP_TOKEN
FRP_TOKEN=${FRP_TOKEN:-"your-token"}

# 本地配置
echo ""
echo -e "${BOLD}💻 配置本地服务：${NC}"
input_prompt "本地 IP 地址 [10.0.0.2]: "
read LOCAL_IP
LOCAL_IP=${LOCAL_IP:-"10.0.0.2"}

input_prompt "Web Manager 端口 [8081]: "
read WEB_PORT
WEB_PORT=${WEB_PORT:-"8081"}

input_prompt "远程访问端口 [8081]: "
read REMOTE_PORT
REMOTE_PORT=${REMOTE_PORT:-"8081"}

# 确认配置
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}📋 配置确认${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  硬件架构：${YELLOW}$FRP_ARCH${NC}"
echo -e "${CYAN}║${NC}  FRP 版本：  ${YELLOW}v$FRP_VERSION${NC}"
echo -e "${CYAN}║${NC}  FRP 服务器：${YELLOW}$FRP_SERVER:$FRP_PORT${NC}"
echo -e "${CYAN}║${NC}  Token:     ${YELLOW}$FRP_TOKEN${NC}"
echo -e "${CYAN}║${NC}  本地 IP:   ${YELLOW}$LOCAL_IP${NC}"
echo -e "${CYAN}║${NC}  Web 端口：  ${YELLOW}$WEB_PORT${NC}"
echo -e "${CYAN}║${NC}  远程端口：${YELLOW}$REMOTE_PORT${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
input_prompt "确认配置并开始安装？(y/n，默认 y): "
read CONFIRM
if [ "$CONFIRM" = "n" ]; then
    print_error "已取消安装"
    exit 0
fi

# ==================== 第二阶段：安装 ====================
print_stage "📦 第二阶段：安装部署"

print_step "安装系统依赖..."
apt update -qq
apt install -y -qq python3-pip git python3-flask

print_step "创建安装目录..."
mkdir -p $INSTALL_DIR
mkdir -p $FRP_DIR
cd $INSTALL_DIR

print_step "下载 frp ${FRP_VERSION} (linux-${FRP_ARCH})..."
cd /tmp
FRP_FILE="frp_${FRP_VERSION}_linux-${FRP_ARCH}.tar.gz"
FRP_URL="https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/${FRP_FILE}"

if ! curl -sL -o ${FRP_FILE} ${FRP_URL}; then
    print_error "下载失败，请检查版本号是否正确"
    exit 1
fi

if ! tar -xzf ${FRP_FILE}; then
    print_error "解压失败，文件可能损坏或版本号错误"
    exit 1
fi

print_step "安装 frpc 到 ${FRP_DIR}..."
cp frp_${FRP_VERSION}_linux-${FRP_ARCH}/frpc ${FRP_DIR}/
chmod +x ${FRP_DIR}/frpc

print_step "创建 frpc 配置文件..."
cat > ${FRP_DIR}/frpc.toml << EOF
serverAddr = "$FRP_SERVER"
serverPort = $FRP_PORT
auth.token = "$FRP_TOKEN"
transport.tcpMux = true
log.level = "info"
log.maxDays = 3

[[proxies]]
name = "web-manager"
type = "tcp"
localIP = "$LOCAL_IP"
localPort = $WEB_PORT
remotePort = $REMOTE_PORT
EOF

chown $SUDO_USER:$SUDO_USER ${FRP_DIR}/frpc.toml
chmod 644 ${FRP_DIR}/frpc.toml

print_step "配置 systemd 服务..."
cd $INSTALL_DIR
cp frp-web-manager.service /etc/systemd/system/
cp frpc.service /etc/systemd/system/

print_step "配置 sudo 权限..."
cat > /etc/sudoers.d/frp-web-manager << EOF
# FRP Web Manager 权限
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart $FRPC_SERVICE
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop $FRPC_SERVICE
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start $FRPC_SERVICE
$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active $FRPC_SERVICE
EOF
chmod 440 /etc/sudoers.d/frp-web-manager

print_step "重载 systemd 配置..."
systemctl daemon-reload

print_step "启动服务..."
systemctl enable $SERVICE_NAME $FRPC_SERVICE >/dev/null 2>&1
systemctl restart $SERVICE_NAME $FRPC_SERVICE

# ==================== 完成 ====================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}✅ 部署完成！${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}📊 服务状态:${NC}"
echo -e "${GREEN}║${NC}"

# 获取服务状态
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}║${NC}  ${GREEN}✓${NC} FRP Web Manager: ${BOLD}运行中${NC}"
else
    echo -e "${GREEN}║${NC}  ${YELLOW}⚠${NC} FRP Web Manager: ${BOLD}未运行${NC}"
fi

if systemctl is-active --quiet $FRPC_SERVICE; then
    echo -e "${GREEN}║${NC}  ${GREEN}✓${NC} FRP Client:      ${BOLD}运行中${NC}"
else
    echo -e "${GREEN}║${NC}  ${YELLOW}⚠${NC} FRP Client:      ${BOLD}未运行${NC}"
fi

echo -e "${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}🌐 访问地址:${NC}"
echo -e "${GREEN}║${NC}  ${CYAN}http://$(hostname -I | awk '{print $1}'):${WEB_PORT}${NC}"
echo -e "${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}📝 日志查看:${NC}"
echo -e "${GREEN}║${NC}  journalctl -u $SERVICE_NAME -f"
echo -e "${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
