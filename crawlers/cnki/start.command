#!/bin/bash
# 知网爬虫一键安装与启动脚本

echo "=========================================="
echo "  知网学术文献爬虫 - 安装启动脚本"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python"
    echo "   访问: https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Python3 已安装: $(python3 --version)"

# 检查Chrome
check_chrome() {
    if command -v google-chrome &> /dev/null; then
        return 0
    elif [ -d "/Applications/Google Chrome.app" ]; then
        return 0
    fi
    return 1
}

# 检查Firefox
check_firefox() {
    if command -v firefox &> /dev/null; then
        return 0
    elif [ -d "/Applications/Firefox.app" ]; then
        return 0
    fi
    return 1
}

# 检查Safari
check_safari() {
    if [ -d "/Applications/Safari.app" ]; then
        return 0
    fi
    return 1
}

# 浏览器检测
BROWSER=""
if check_chrome; then
    BROWSER="Chrome"
elif check_firefox; then
    BROWSER="Firefox"
elif check_safari; then
    BROWSER="Safari"
fi

if [ -z "$BROWSER" ]; then
    echo ""
    echo "⚠️  未检测到浏览器，请先安装:"
    echo "   1. Chrome: https://www.google.com/chrome/"
    echo "   2. 或 Firefox: https://www.mozilla.org/firefox/"
    echo ""
    read -p "按回车键退出或输入'y'继续(可能报错)..."
    if [ "$REPLY" != "y" ] && [ "$REPLY" != "Y" ]; then
        exit 0
    fi
else
    echo "✅ 检测到浏览器: $BROWSER"
fi

# 安装依赖
echo ""
echo "📦 安装Python依赖..."
pip3 install -q selenium webdriver-manager beautifulsoup4 lxml pandas 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ 依赖安装完成"
else
    echo "⚠️ 部分依赖安装失败，尝试继续..."
fi

# 启动GUI
echo ""
echo "🚀 启动知网爬虫..."
echo "   (请勿关闭弹出的浏览器窗口)"
echo ""

python3 launcher.py

echo ""
echo "程序已退出"
