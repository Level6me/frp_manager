#!/bin/bash

# FRP Web Manager v1.8.0 - 一键部署脚本
# 功能：实时获取 frp 最新版本号 + 自动检测本机 IP + 下载验证 + 实时进度 + 版本可用性验证
# 修复：frp 文件名规则 linux_arm64 (下划线) + 版本选择逻辑 + 支持本地压缩包 + 30 秒超时 + 防止 set -e 退出
# 修复：本地压缩包解压后动态获取目录名 + systemd 服务文件改为脚本内生成
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

# 获取最新版本号（只获取正式 release，排除 pre-release）
get_latest_frp_version() {
    local latest=$(curl -s "https://api.github.com/repos/fatedier/frp/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' | sed 's/^v//')
    if [ -n "$latest" ]; then
        echo "$latest"
    else
        echo "0.61.1"  # fallback
    fi
}

# 获取最新 5 个正式版本（排除 pre-release 和 draft）
get_recent_frp_versions() {
    curl -s "https://api.github.com/repos/fatedier/frp/releases?per_page=10" | \
    python3 -c "
import sys, json
releases = json.load(sys.stdin)
for r in releases:
    if not r.get('prerelease') and not r.get('draft'):
        tag = r.get('tag_name', '')
        if tag.startswith('v'):
            print(tag[1:])
" | head -n 5
}

# 选择 frpc 版本
echo ""
echo -e "${YELLOW}🔄${NC} 正在获取 frp 最新版本..."
LATEST_VERSION=$(get_latest_frp_version)
print_success "当前最新版本：v${LATEST_VERSION}"

# 验证最新版本是否可下载（30 秒超时，仅提示不强制切换）
echo -e "${YELLOW}🔍${NC} 验证版本 v${LATEST_VERSION} 可用性...（30 秒超时）"
TEST_URL="https://github.com/fatedier/frp/releases/download/v${LATEST_VERSION}/frp_${LATEST_VERSION}_linux_${FRP_ARCH}.tar.gz"
TEST_CODE=$(curl -sL --max-time 30 -w "%{http_code}" -o /dev/null "${TEST_URL}" || echo "000")
if [ "$TEST_CODE" != "200" ]; then
    if [ "$TEST_CODE" = "000" ] || [ -z "$TEST_CODE" ]; then
        print_warn "验证超时（>30 秒），网络可能不通"
    else
        print_warn "最新版本 v${LATEST_VERSION} 可能无法下载 (HTTP ${TEST_CODE})"
    fi
    print_warn "你可以选择其他版本或使用本地已有的压缩包"
fi

echo ""
echo -e "${BOLD}📦 选择 frpc 版本：${NC}"
echo -e "   ${GREEN}1)${NC} 最新版本 (v${LATEST_VERSION})"
echo -e "   ${GREEN}2)${NC} 从最近 5 个版本中选择"
echo -e "   ${GREEN}3)${NC} 自定义版本"
echo -e "   ${GREEN}4)${NC} 使用本地已有的压缩包"
echo ""
input_prompt "请输入选项 (1/2/3/4，默认 1): "
read VERSION_CHOICE

case $VERSION_CHOICE in
    2)
        echo ""
        echo -e "${YELLOW}🔄${NC} 正在获取最近 5 个版本..."
        mapfile -t VERSIONS < <(get_recent_frp_versions)
        
        # 如果获取失败，使用默认版本列表
        if [ ${#VERSIONS[@]} -eq 0 ]; then
            print_warn "无法获取版本列表，使用默认版本"
            VERSIONS=("0.61.1" "0.61.0" "0.60.0" "0.59.0" "0.58.0")
        fi
        
        echo -e "${BOLD}可选择的版本：${NC}"
        for i in "${!VERSIONS[@]}"; do
            echo -e "   ${GREEN}$((i+1)))${NC} v${VERSIONS[$i]}"
        done
        echo ""
        input_prompt "请选择版本 (1-${#VERSIONS[@]}，默认 1): "
        read VERSION_SELECT
        if [ -z "$VERSION_SELECT" ] || [ "$VERSION_SELECT" -lt 1 ] || [ "$VERSION_SELECT" -gt "${#VERSIONS[@]}" ]; then
            FRP_VERSION="${VERSIONS[0]}"
        else
            FRP_VERSION="${VERSIONS[$((VERSION_SELECT-1))]}"
        fi
        print_success "已选择版本：v${FRP_VERSION}"
        ;;
    3)
        echo ""
        input_prompt "请输入自定义版本号 (如：0.54.0): "
        read CUSTOM_VERSION
        FRP_VERSION="$CUSTOM_VERSION"
        ;;
    4)
        echo ""
        echo -e "${BOLD}📦 请使用本地 frp 压缩包：${NC}"
        input_prompt "请输入压缩包完整路径 [/tmp/frp.tar.gz]: "
        read LOCAL_FRP_PATH
        LOCAL_FRP_PATH=${LOCAL_FRP_PATH:-"/tmp/frp.tar.gz"}
        
        # 验证文件是否存在
        if [ ! -f "$LOCAL_FRP_PATH" ]; then
            print_error "文件不存在：$LOCAL_FRP_PATH"
            exit 1
        fi
        
        # 验证文件类型
        FILE_TYPE=$(file -b "$LOCAL_FRP_PATH" 2>/dev/null | head -c 20)
        if ! echo "$FILE_TYPE" | grep -qi "gzip\|compress"; then
            print_error "文件不是 gzip 格式 (检测到：${FILE_TYPE})"
            exit 1
        fi
        
        print_success "使用本地文件：$LOCAL_FRP_PATH"
        USE_LOCAL_FILE="yes"
        ;;
    *)
        FRP_VERSION="$LATEST_VERSION"
        ;;
esac

# 自动获取本机局域网 IP
echo -e "${YELLOW}🔍${NC} 检测本机局域网 IP..."
AUTO_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')
if [ -z "$AUTO_IP" ]; then
    AUTO_IP=$(hostname -I | awk '{print $1}')
fi
if [ -z "$AUTO_IP" ]; then
    AUTO_IP="192.168.1.100"  # fallback 默认值
fi

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
print_success "自动检测本机 IP: ${AUTO_IP}"
input_prompt "本地 IP 地址 [${AUTO_IP}]: "
read MANUAL_IP
LOCAL_IP=${MANUAL_IP:-"$AUTO_IP"}

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
apt install -y -qq python3-pip python3-flask

print_step "创建安装目录..."
mkdir -p $INSTALL_DIR
mkdir -p $FRP_DIR
cd $INSTALL_DIR

# 检查是否使用本地文件
if [ "$USE_LOCAL_FILE" = "yes" ]; then
    print_step "使用本地 frp 压缩包..."
    cd /tmp
    FRP_FILE="$LOCAL_FRP_PATH"
    FILE_SIZE=$(stat -c%s "${FRP_FILE}" 2>/dev/null || stat -f%z "${FRP_FILE}" 2>/dev/null)
    print_success "本地文件 (${FILE_SIZE} 字节)"
    
    if ! tar -xzf ${FRP_FILE}; then
        print_error "解压失败，文件可能损坏"
        exit 1
    fi
    
    # 动态获取解压后的目录名（本地文件不知道版本号）
    FRP_DIR_NAME=$(tar -tzf ${FRP_FILE} | head -1 | cut -f1 -d"/")
    print_step "检测到解压目录：${FRP_DIR_NAME}"
else
    print_step "下载 frp ${FRP_VERSION} (linux_${FRP_ARCH})..."
    cd /tmp
    FRP_FILE="frp_${FRP_VERSION}_linux_${FRP_ARCH}.tar.gz"
    FRP_URL="https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/${FRP_FILE}"
    echo -e "${CYAN}  URL: ${FRP_URL}${NC}"
    
    # 下载并检查 HTTP 状态码（显示进度条）
    HTTP_CODE=$(curl --progress-bar -w "%{http_code}" -o ${FRP_FILE} ${FRP_URL})
    if [ "$HTTP_CODE" != "200" ]; then
        print_error "下载失败 (HTTP ${HTTP_CODE})，版本号 v${FRP_VERSION} 可能不存在"
        print_error "请检查版本号是否正确，或选择其他版本"
        rm -f ${FRP_FILE}
        exit 1
    fi
    
    # 验证文件大小
    FILE_SIZE=$(stat -c%s "${FRP_FILE}" 2>/dev/null || stat -f%z "${FRP_FILE}" 2>/dev/null)
    if [ "$FILE_SIZE" -lt 1000 ]; then
        print_error "下载的文件过小 (${FILE_SIZE} 字节)，可能不是有效的压缩包"
        print_error "请检查网络连接或版本号"
        rm -f ${FRP_FILE}
        exit 1
    fi
    
    # 验证文件类型（必须是 gzip）
    FILE_TYPE=$(file -b ${FRP_FILE} 2>/dev/null | head -c 20)
    if ! echo "$FILE_TYPE" | grep -qi "gzip\|compress"; then
        print_error "下载的文件不是 gzip 格式 (检测到：${FILE_TYPE})"
        print_error "可能是 GitHub 返回了错误页面"
        rm -f ${FRP_FILE}
        exit 1
    fi
    
    print_success "下载完成 (${FILE_SIZE} 字节)"
    
    if ! tar -xzf ${FRP_FILE}; then
        print_error "解压失败，文件可能损坏"
        rm -f ${FRP_FILE}
        exit 1
    fi
fi

print_step "安装 frpc 到 ${FRP_DIR}..."
if [ "$USE_LOCAL_FILE" = "yes" ]; then
    # 使用动态获取的目录名
    cp ${FRP_DIR_NAME}/frpc ${FRP_DIR}/
else
    # 使用版本号构建目录名（下划线）
    cp frp_${FRP_VERSION}_linux_${FRP_ARCH}/frpc ${FRP_DIR}/
fi
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

# 生成 frp-web-manager.service
cat > /etc/systemd/system/frp-web-manager.service << EOF
[Unit]
Description=FRP Web Manager
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 生成 frpc.service
cat > /etc/systemd/system/frpc.service << EOF
[Unit]
Description=FRP Client
After=network.target

[Service]
Type=simple
User=$SUDO_USER
ExecStart=${FRP_DIR}/frpc -c ${FRP_DIR}/frpc.toml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

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
