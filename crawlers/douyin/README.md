# 抖音爬虫工具包

功能强大的抖音视频爬虫，支持抓取视频信息和评论区数据。

## 功能特点

- 视频信息抓取（标题、作者、点赞数、评论数等）
- 评论区数据采集（支持增量翻页）
- Excel 导出功能
- 批量爬取
- 本地 HTML 解析

## 安装依赖

```bash
pip install requests httpx playwright pandas openpyxl beautifulsoup4
playwright install chromium
```

## 使用方法

### 基本用法

```bash
# 抓取默认视频的评论
python3 douyin_scraper.py

# 指定视频 URL
python3 douyin_scraper.py https://www.douyin.com/video/xxxxx

# 指定最大评论数
python3 douyin_scraper.py --max 100

# 无头模式（不显示浏览器）
python3 douyin_scraper.py --headless

# 批量爬取（urls.txt 中每行一个 URL）
python3 douyin_scraper.py --urls urls.txt

# 解析本地 HTML 文件
python3 douyin_scraper.py --local page.html
```

### 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `url` | 抖音视频 URL | `python3 douyin_scraper.py <url>` |
| `--max N` | 最大评论数 | `--max 50` |
| `--headless` | 无头模式 | `--headless` |
| `--urls FILE` | 批量文件 | `--urls urls.txt` |
| `--local FILE` | 本地 HTML | `--local page.html` |
| `--output DIR` | 输出目录 | `--output ./data` |

## 输出格式

- JSON 格式的评论数据
- Excel 格式的表格数据（带格式美化）
- 视频信息 JSON 文件

## 注意事项

1. 请遵守抖音平台的使用条款
2. 不要过于频繁地请求，以免被封禁
3. 爬取的数据仅供学习研究使用

## 技术栈

- Playwright（浏览器自动化）
- httpx（异步 HTTP 客户端）
- pandas + openpyxl（数据导出）
- BeautifulSoup4（HTML 解析）
