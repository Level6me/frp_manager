#!/bin/bash
# FRP Web Manager - 一键同步更新脚本
set -e

INSTALL_DIR="/opt/frp-web-manager"
TMP_DIR="/tmp/frp_manager_update"

echo "=========================================="
echo "🚀 FRP Web Manager 正在同步更新..."
echo "=========================================="

# 1. 创建临时目录并从 GitHub 解压最新代码包
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

echo "📥 正在拉取远程 GitHub 最新代码..."
curl -sL https://github.com/Level6me/frp_manager/archive/refs/heads/main.tar.gz | tar -xz -C "$TMP_DIR" --strip-components=1

# 2. 同步代码文件至 /opt/frp-web-manager
if [ -d "$INSTALL_DIR" ]; then
    echo "📦 正在同步代码文件至系统运行路径 $INSTALL_DIR ..."
    sudo cp -f "$TMP_DIR/app.py" "$INSTALL_DIR/"
    sudo cp -rf "$TMP_DIR/templates" "$INSTALL_DIR/"
    sudo cp -rf "$TMP_DIR/static" "$INSTALL_DIR/"
    if [ -f "$TMP_DIR/deploy.sh" ]; then
        sudo cp -f "$TMP_DIR/deploy.sh" "$INSTALL_DIR/"
    fi
    echo "✓ 代码已成功覆盖至 $INSTALL_DIR"
fi

# 3. 清理临时目录
rm -rf "$TMP_DIR"

# 4. 重启 systemd 服务
echo "🔄 正在重启 frp-web-manager 与 frpc 服务..."
if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl daemon-reload 2>/dev/null || true
    sudo systemctl restart frp-web-manager 2>/dev/null || true
    sudo systemctl restart frpc 2>/dev/null || true
fi

echo "=========================================="
echo "✅ 更新完成！请直接刷新网页查看最新数据看板。"
echo "=========================================="
