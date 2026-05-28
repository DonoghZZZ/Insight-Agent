#!/usr/bin/env python3
"""
知乎回答爬虫 v1 — 支持滚动加载与本地HTML解析

用法:
  python3 zhihu_scraper.py                                    # 默认URL
  python3 zhihu_scraper.py <知乎问题URL>                      # 指定URL
  python3 zhihu_scraper.py --max 50                           # 限制最多50条回答
  python3 zhihu_scraper.py --headless                         # headless模式
  python3 zhihu_scraper.py --local <本地HTML文件路径>          # 解析本地HTML（测试模式）
"""

import sys
import os
import re
import time
import logging
import argparse
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.browser import STEALTH_JS, DEFAULT_USER_AGENT, DEFAULT_VIEWPORT, BROWSER_ARGS
from common.login_helper import (
    ensure_session, get_smart_headless, is_session_valid,
    mark_session_valid, ZHIHU_CHECK_LOGIN_JS,
)

# ========== 自动安装依赖 ==========

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright", "-q"], check=True)
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl", "-q"], check=True)
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "beautifulsoup4", "-q"], check=True)
    from bs4 import BeautifulSoup

# ========== 路径与常量 ==========

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DEFAULT_URL = "https://www.zhihu.com/question/65384083/answer/73753437178"
MAX_ANSWERS = 100
SCROLL_ROUNDS = 50
SCROLL_WAIT_MS = 1200
NO_CHANGE_THRESHOLD = 5
RETRY_TIMES = 3

# ========== 日志配置 ==========

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("zhihu_scraper")


def log(msg: str, level: str = "info"):
    """输出日志"""
    if level == "info":
        logger.info(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    elif level == "debug":
        logger.debug(msg)


# ========== 命令行参数 ==========

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="知乎回答爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 zhihu_scraper.py
  python3 zhihu_scraper.py https://www.zhihu.com/question/123
  python3 zhihu_scraper.py --max 50 --headless
  python3 zhihu_scraper.py --local /path/to/local.html
        """,
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        help=f"目标知乎问题URL（默认: {DEFAULT_URL}）",
    )
    parser.add_argument(
        "--max",
        dest="max_answers",
        type=int,
        default=MAX_ANSWERS,
        help=f"最多爬取回答数（默认: {MAX_ANSWERS}）",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="使用headless模式运行浏览器（默认: False）",
    )
    parser.add_argument(
        "--local",
        dest="local_file",
        default=None,
        help="解析本地HTML文件路径（测试模式，不走浏览器）",
    )
    parser.add_argument(
        "--output",
        dest="output_file",
        default=None,
        help="指定输出Excel文件路径",
    )
    return parser.parse_args()


# ========== 浏览器配置 ==========

def create_browser_context(p, headless: bool = False):
    """创建浏览器上下文（带反检测）"""
    profile_dir = os.path.join(SCRIPT_DIR, "browser_profile")
    os.makedirs(profile_dir, exist_ok=True)

    context = p.chromium.launch_persistent_context(
        profile_dir,
        headless=headless,
        args=BROWSER_ARGS + [
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            "--disable-features=BlockInsecurePrivateNetworkRequests",
            "--disable-setuid-sandbox",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--window-size=1280,900",
            "--start-maximized",
        ],
        viewport={"width": 1280, "height": 900},
        user_agent=DEFAULT_USER_AGENT,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        permissions=["geolocation"],
        java_script_enabled=True,
        bypass_csp=True,
    )
    return context


# ========== 反检测JS ==========

ANTI_DETECTION_JS = f"""() => {{
{STEALTH_JS}
}}"""


# ========== 浏览器端JS提取逻辑 ==========

EXTRACT_ANSWERS_JS = """
() => {
    const results = [];
    const seen = new Set();

    // 知乎回答容器选择器（多种备选）
    const containerSelectors = [
        '.ContentItem.AnswerItem',
        '.AnswerCard',
        '[data-za-detail-view-path-module="AnswerItem"]',
    ];

    let containers = [];
    for (const sel of containerSelectors) {
        const els = document.querySelectorAll(sel);
        if (els.length > 0) {
            containers = Array.from(els);
            break;
        }
    }

    // 兜底：尝试通过内容特征识别
    if (containers.length === 0) {
        const allEls = document.querySelectorAll('div');
        containers = Array.from(allEls).filter(el => {
            return el.querySelector('.AuthorInfo-name') !== null
                && el.querySelector('.RichContent-inner, .RichText') !== null;
        });
    }

    containers.forEach(el => {
        // 作者昵称
        const nameEl = el.querySelector('.AuthorInfo-name, [class*="AuthorInfo-name"]');
        const name = nameEl ? nameEl.innerText.trim() : '';

        // 作者简介/头衔
        const headlineEl = el.querySelector('.AuthorInfo-headline, [class*="AuthorInfo-headline"]');
        const headline = headlineEl ? headlineEl.innerText.trim() : '';

        // 认证信息
        const badgeEl = el.querySelector('.AuthorInfo-badgeText, [class*="AuthorInfo-badge"]');
        const badge = badgeEl ? badgeEl.innerText.trim() : '';

        // 回答内容（纯文本）
        const contentSelectors = [
            '.RichContent-inner',
            '.RichText',
            '.CopyrightRichText-richText',
            '[class*="RichContent-inner"]',
            '[class*="RichText"]',
        ];
        let content = '';
        for (const sel of contentSelectors) {
            const contentEl = el.querySelector(sel);
            if (contentEl) {
                content = contentEl.innerText.trim();
                break;
            }
        }

        // 发布时间
        const timeEl = el.querySelector('.ContentItem-time, [class*="ContentItem-time"]');
        let publish_time = '';
        if (timeEl) {
            publish_time = timeEl.innerText.trim();
        } else {
            // 尝试从data属性或title提取
            const timeAlt = el.querySelector('[data-tooltip]');
            if (timeAlt && timeAlt.getAttribute('data-tooltip').match(/\\d{4}/)) {
                publish_time = timeAlt.getAttribute('data-tooltip');
            }
        }

        // 赞同数
        let upvotes = 0;
        const voteBtnSelectors = [
            '.VoteButton',
            'button[class*="VoteButton"]',
            '[class*="VoteButton"]',
        ];
        for (const sel of voteBtnSelectors) {
            const voteBtn = el.querySelector(sel);
            if (voteBtn) {
                const text = voteBtn.innerText || voteBtn.textContent || '';
                const match = text.match(/赞同\\s*(\\d+)/);
                if (match) {
                    upvotes = parseInt(match[1], 10);
                    break;
                }
                // 处理"赞同"但没有数字的情况（0赞同）
                if (text.includes('赞同') && !text.match(/\\d/)) {
                    upvotes = 0;
                    break;
                }
            }
        }

        // 评论数
        let comments = 0;
        const actionEls = el.querySelectorAll('.ContentItem-action, [class*="ContentItem-action"]');
        actionEls.forEach(a => {
            const text = (a.innerText || a.textContent || '').trim();
            const match = text.match(/评论\\s*(\\d+)/);
            if (match) {
                comments = parseInt(match[1], 10);
            }
            // 处理"评论"但没有数字的情况
            if (text === '评论' || text === '评论 ' || text === '添加评论') {
                comments = 0;
            }
        });

        // 是否推荐回答
        let isRecommended = false;
        // 方式1：查找包含"推荐"文本的元素
        const recEls = el.querySelectorAll('*');
        for (const recEl of recEls) {
            const text = (recEl.innerText || '').trim();
            if (text === '推荐' && recEl.children.length === 0) {
                isRecommended = true;
                break;
            }
        }
        // 方式2：检查class或data属性
        if (!isRecommended) {
            const elText = el.innerText || '';
            if (elText.includes('推荐回答') || elText.includes('精选回答')) {
                isRecommended = true;
            }
        }

        // 去重键：作者+内容前50字
        const key = (name + '|' + content.slice(0, 50)).trim();
        if (key && !seen.has(key) && content.length > 0) {
            seen.add(key);
            results.push({
                name,
                headline,
                badge,
                content,
                publish_time,
                upvotes,
                comments,
                isRecommended,
            });
        }
    });

    return results;
}
"""


# ========== 本地HTML解析 ==========

def parse_local_html(file_path: str) -> List[Dict[str, Any]]:
    """解析本地保存的知乎HTML文件"""
    log(f"📄 解析本地HTML文件: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    # 查找回答容器
    containers = soup.find_all("div", class_=lambda x: x and "AnswerItem" in x)
    if not containers:
        # 兜底：查找同时包含作者名和内容的div
        all_divs = soup.find_all("div")
        for div in all_divs:
            if div.find(class_=lambda x: x and "AuthorInfo-name" in str(x)):
                if div.find(class_=lambda x: x and "RichContent" in str(x)):
                    containers.append(div)

    log(f"   找到 {len(containers)} 个回答容器")

    for idx, el in enumerate(containers):
        # 作者昵称
        name_el = el.find(class_=lambda x: x and "AuthorInfo-name" in str(x))
        name = name_el.get_text(strip=True) if name_el else ""

        # 作者简介
        headline_el = el.find(class_=lambda x: x and "AuthorInfo-headline" in str(x))
        headline = headline_el.get_text(strip=True) if headline_el else ""

        # 认证信息
        badge_el = el.find(class_=lambda x: x and "AuthorInfo-badge" in str(x))
        badge = badge_el.get_text(strip=True) if badge_el else ""

        # 回答内容
        content_el = (
            el.find(class_="RichContent-inner")
            or el.find(class_=lambda x: x and "RichText" in str(x))
            or el.find(class_=lambda x: x and "CopyrightRichText" in str(x))
        )
        content = content_el.get_text(strip=True) if content_el else ""

        # 发布时间
        time_el = el.find(class_=lambda x: x and "ContentItem-time" in str(x))
        publish_time = time_el.get_text(strip=True) if time_el else ""

        # 赞同数
        upvotes = 0
        vote_btn = el.find(class_=lambda x: x and "VoteButton" in str(x))
        if vote_btn:
            text = vote_btn.get_text(strip=True)
            match = re.search(r"赞同\s*(\d+)", text)
            if match:
                upvotes = int(match.group(1))

        # 评论数
        comments = 0
        action_els = el.find_all(class_=lambda x: x and "ContentItem-action" in str(x))
        for a in action_els:
            text = a.get_text(strip=True)
            match = re.search(r"评论\s*(\d+)", text)
            if match:
                comments = int(match.group(1))

        # 是否推荐
        isRecommended = False
        if "推荐" in el.get_text():
            # 更精确判断：查找纯文本"推荐"
            for tag in el.find_all(string=lambda text: text and text.strip() == "推荐"):
                isRecommended = True
                break

        # 去重
        key = (name + "|" + content[:50]).strip()
        if key and key not in seen and content:
            seen.add(key)
            results.append({
                "name": name,
                "headline": headline,
                "badge": badge,
                "content": content,
                "publish_time": publish_time,
                "upvotes": upvotes,
                "comments": comments,
                "isRecommended": isRecommended,
            })

    log(f"   ✅ 解析完成，共 {len(results)} 条有效回答")
    return results


# ========== Playwright 爬取 ==========

def scrape_with_playwright(
    url: str,
    max_answers: int = MAX_ANSWERS,
    headless: bool = False,
) -> List[Dict[str, Any]]:
    """使用Playwright爬取知乎回答"""
    # 智能决定是否 headless
    headless = get_smart_headless("zhihu", headless)
    log(f"🌐 启动浏览器 (headless={headless})")
    log(f"📄 目标URL: {url}")

    all_answers = []
    seen_keys = set()

    with sync_playwright() as p:
        # 预检查浏览器
        import subprocess

        r = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True,
            text=True,
        )
        if "already" not in r.stdout and "already" not in r.stderr:
            log("⚠️ 安装 Playwright Chromium...")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
            )
            log("✅ 浏览器安装完成")

        context = create_browser_context(p, headless=headless)
        page = context.new_page()
        page.add_init_script(STEALTH_JS)

        try:
            # ===== 登录检查（统一 session 管理） =====
            logged_in = ensure_session(page, "zhihu")
            if not logged_in:
                log("⚠️ 未登录，部分内容可能无法获取", level="warning")

            # 打开页面
            log("⏳ 正在加载页面...")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # 运行中二次检查：如果被重定向到登录页
            if "login" in page.url.lower() or "signin" in page.url.lower():
                log("🔑 页面被重定向到登录页，请在浏览器中登录...", level="warning")
                from common.login_helper import check_and_login_if_needed
                check_and_login_if_needed(page, "zhihu")
                # 重新加载目标页
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

            # 等待回答加载
            try:
                page.wait_for_selector(".ContentItem.AnswerItem, .AnswerCard", timeout=15000)
            except PwTimeout:
                log("⚠️ 等待回答容器超时，继续尝试...", level="warning")

            page.wait_for_timeout(2000)

            # 尝试点击"查看全部回答"按钮（知乎需要点击才会加载更多）
            try:
                view_all_btn = page.locator("text=查看全部").first
                if view_all_btn.is_visible(timeout=5000):
                    log("   🖱️ 点击'查看全部回答'按钮...")
                    view_all_btn.click()
                    page.wait_for_timeout(5000)
                    log("   ✅ 已展开全部回答")
            except Exception:
                pass

            # 等待更多回答加载
            page.wait_for_timeout(3000)

            # 滚动加载
            log(f"📜 开始滚动加载 (上限 {max_answers} 条)...")
            last_count = 0
            no_change = 0

            for rnd in range(SCROLL_ROUNDS):
                # 滚动到底部
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(SCROLL_WAIT_MS)

                # 尝试点击"展开阅读全文"按钮
                try:
                    expand_btns = page.locator("button:has-text('阅读全文'), text=展开").all()
                    for btn in expand_btns[:5]:
                        try:
                            if btn.is_visible(timeout=500):
                                btn.click(timeout=1000)
                                page.wait_for_timeout(800)
                        except Exception:
                            pass
                except Exception:
                    pass

                # 提取当前数据
                answers = page.evaluate(EXTRACT_ANSWERS_JS)

                # 合并去重
                new_count = 0
                for ans in answers:
                    key = (ans.get("name", "") + "|" + ans.get("content", "")[:50]).strip()
                    if key and key not in seen_keys:
                        seen_keys.add(key)
                        all_answers.append(ans)
                        new_count += 1

                cur = len(all_answers)

                if cur == last_count:
                    no_change += 1
                    if no_change >= NO_CHANGE_THRESHOLD:
                        log(f"   ✓ 连续{NO_CHANGE_THRESHOLD}轮无新数据，停止滚动")
                        break
                else:
                    no_change = 0
                    if rnd % 3 == 0:
                        log(f"   ... 当前 {cur} 条回答")

                last_count = cur
                if cur >= max_answers:
                    log(f"   ✓ 已达上限 {max_answers} 条")
                    break

            log(f"   ✅ 滚动结束，共 {len(all_answers)} 条回答")

        except Exception as e:
            log(f"❌ 爬取过程出错: {e}", level="error")
            import traceback

            traceback.print_exc()
        finally:
            context.close()
            log("🔒 浏览器已关闭")

    return all_answers


# ========== Excel 导出 ==========

def save_to_excel(answers: List[Dict[str, Any]], filepath: str):
    """将回答数据保存为Excel文件"""
    log(f"📊 正在生成Excel: {filepath}")

    wb = Workbook()
    ws = wb.active
    ws.title = "知乎回答数据"

    # 样式定义
    header_font = Font(name="Microsoft YaHei", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="FF2F5496", end_color="FF2F5496", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    data_font = Font(name="Microsoft YaHei", size=10)
    data_align = Alignment(vertical="top", wrap_text=True)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side("thin", "FFD0D0D0"),
        right=Side("thin", "FFD0D0D0"),
        top=Side("thin", "FFD0D0D0"),
        bottom=Side("thin", "FFD0D0D0"),
    )

    # 表头
    headers = [
        "序号",
        "回答者昵称",
        "回答者简介/头衔",
        "认证信息",
        "回答内容",
        "发布时间",
        "赞同数",
        "评论数",
        "是否推荐回答",
    ]
    widths = [6, 18, 25, 20, 80, 18, 10, 10, 14]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
        ws.column_dimensions[chr(64 + col)].width = w

    # 数据行
    for i, ans in enumerate(answers, 1):
        row_data = [
            i,
            ans.get("name", ""),
            ans.get("headline", ""),
            ans.get("badge", ""),
            ans.get("content", ""),
            ans.get("publish_time", ""),
            ans.get("upvotes", 0),
            ans.get("comments", 0),
            "是" if ans.get("isRecommended", False) else "否",
        ]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=i + 1, column=col, value=val)
            cell.font = data_font
            cell.border = thin_border
            if col in (1, 7, 8, 9):
                cell.alignment = center_align
            else:
                cell.alignment = data_align

    # 冻结首行 + 自动筛选
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:I{len(answers) + 1}"

    # 调整行高
    for row in range(2, len(answers) + 2):
        ws.row_dimensions[row].height = None  # 自动

    wb.save(filepath)
    log(f"   ✅ Excel已保存: {filepath}")
    return filepath


# ========== 主程序 ==========

def main():
    args = parse_args()

    print(f"\n{'='*70}")
    print(f"  知乎回答爬虫 v1")
    print(f"{'='*70}")

    answers = []

    if args.local_file:
        # 本地HTML解析模式
        print(f"  模式: 本地HTML解析")
        print(f"  文件: {args.local_file}")
        print(f"{'='*70}\n")
        try:
            answers = parse_local_html(args.local_file)
        except Exception as e:
            log(f"❌ 解析本地文件失败: {e}", level="error")
            import traceback

            traceback.print_exc()
            sys.exit(1)
    else:
        # Playwright在线爬取模式
        print(f"  模式: 在线爬取")
        print(f"  URL: {args.url}")
        print(f"  最大回答数: {args.max_answers}")
        print(f"  Headless: {args.headless}")
        print(f"{'='*70}\n")

        # 重试机制
        for attempt in range(1, RETRY_TIMES + 1):
            try:
                answers = scrape_with_playwright(
                    args.url,
                    max_answers=args.max_answers,
                    headless=args.headless,
                )
                if answers:
                    break
                if attempt < RETRY_TIMES:
                    log(f"⚠️ 第{attempt}次尝试未获取数据，{attempt * 3}秒后重试...", level="warning")
                    time.sleep(attempt * 3)
            except Exception as e:
                log(f"❌ 第{attempt}次尝试失败: {e}", level="error")
                if attempt < RETRY_TIMES:
                    time.sleep(attempt * 3)
                else:
                    raise

    # 去重（最终保险）
    seen = set()
    unique_answers = []
    for ans in answers:
        key = (ans.get("name", "") + "|" + ans.get("content", "")[:50]).strip()
        if key and key not in seen:
            seen.add(key)
            unique_answers.append(ans)

    # 排序：按赞同数降序
    unique_answers.sort(key=lambda x: x.get("upvotes", 0), reverse=True)

    log(f"📦 最终有效回答数: {len(unique_answers)}")

    if not unique_answers:
        log("⚠️ 未获取到任何回答数据", level="warning")
        print(f"\n{'='*70}")
        print(f"  ⚠️ 未获取到数据，请检查URL或网络连接")
        print(f"{'='*70}\n")
        sys.exit(1)

    # 保存Excel
    if args.output_file:
        output_path = args.output_file
    else:
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(OUTPUT_DIR, f"zhihu_answers_{ts}.xlsx")

    save_to_excel(unique_answers, output_path)

    # 统计输出
    total_upvotes = sum(a.get("upvotes", 0) for a in unique_answers)
    total_comments = sum(a.get("comments", 0) for a in unique_answers)
    recommended_count = sum(1 for a in unique_answers if a.get("isRecommended"))

    print(f"\n{'='*70}")
    print(f"  ✅ 爬取完成")
    print(f"  回答总数: {len(unique_answers)}")
    print(f"  推荐回答: {recommended_count}")
    print(f"  总赞同数: {total_upvotes}")
    print(f"  总评论数: {total_comments}")
    print(f"\n  📊 输出文件: {output_path}")
    print(f"{'='*70}\n")

    return output_path


if __name__ == "__main__":
    main()
