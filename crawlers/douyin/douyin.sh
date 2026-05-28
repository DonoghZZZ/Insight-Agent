#!/bin/bash
# 抖音评论爬虫 v4.0
# 用法: ./douyin.sh <视频链接> [最大评论数]
# 示例: ./douyin.sh https://v.douyin.com/xxx/
#       ./douyin.sh https://www.douyin.com/video/123456 5000

cd "$(dirname "$0")"

URL="${1:-https://v.douyin.com/Xlm-0WaC7GI/}"
MAX="${2:-10000}"

echo "📹 抖音评论爬取 v4.0"
echo "   URL: $URL"
echo "   最多: ${MAX}条评论"
echo ""

python3 douyin_scraper.py "$URL" --max $MAX
