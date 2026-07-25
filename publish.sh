#!/bin/bash
# 红楼伏笔 — GitHub 发布脚本
# 在你的电脑上打开终端，cd 到 honglou-meng-foreshadowing 文件夹，运行:
#   bash publish.sh

set -e

echo "🏮 红楼伏笔 — 发布到 GitHub"
echo "================================"

# 1. 检查 git 是否安装
if ! command -v git &> /dev/null; then
    echo "❌ 请先安装 Git: https://git-scm.com/downloads"
    exit 1
fi

# 2. 输入 GitHub 用户名
read -p "你的 GitHub 用户名: " GITHUB_USER
if [ -z "$GITHUB_USER" ]; then
    echo "❌ 用户名不能为空"
    exit 1
fi

REPO_NAME="honglou-meng-foreshadowing"

# 3. 确认
echo ""
echo "即将发布到: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
read -p "确认? (y/n) " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# 4. 清理旧的 git 目录
if [ -d .git ]; then
    echo "清理旧的 .git 目录..."
    rm -rf .git
fi

# 5. 初始化 git
echo ""
echo "📦 初始化 Git 仓库..."
git init
git branch -m main

# 6. 添加所有文件
git add .

# 7. 提交
echo "📝 提交..."
git commit -m "初版发布：红楼伏笔结构化探佚推理系统

60条伏笔 · 40条约束 · 29个人物结局 · 22个重建事件
曹雪芹个人档案 · 学者权威性评级 · 加权推理引擎"

# 8. 关联远程仓库
echo "🔗 关联远程仓库..."
git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git" 2>/dev/null || git remote set-url origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"

# 9. 推送
echo "🚀 推送到 GitHub..."
git push -u origin main

echo ""
echo "================================================"
echo "✅ 发布成功！"
echo ""
echo "📂 仓库地址: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "📋 下一步："
echo "  1. 打开上面的链接"
echo "  2. Settings → Pages → Source: Deploy from a branch"
echo "     Branch: main, Folder: /public, Save"
echo "  3. 等 1-2 分钟，访问:"
echo "     https://$GITHUB_USER.github.io/$REPO_NAME/"
echo "================================================"
