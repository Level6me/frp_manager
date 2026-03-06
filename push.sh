#!/bin/bash

# 快速推送脚本
# 使用：./push.sh "提交信息"

if [ -z "$1" ]; then
    echo "❌ 请提供提交信息"
    echo "用法：./push.sh \"你的提交信息\""
    exit 1
fi

echo "🔄 拉取最新代码..."
git pull

echo ""
echo "📝 提交更改..."
git add .
git commit -m "$1"

echo ""
echo "🚀 推送到 Git 服务器..."
git push

echo ""
echo "✅ 完成！"
