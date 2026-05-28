#!/usr/bin/env python3
"""
知乎批量爬取脚本 — 支持问题回答 + 专栏文章
合并14个链接到一个Excel，带来源链接字段

用法:
  python3 batch_scraper.py                    # 爬取默认列表
  python3 batch_scraper.py --max 20           # 每个链接最多20条
"""

import sys
import os
import re
import time
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.browser import STEALTH_JS, DEFAULT_USER_AGENT, DEFAULT_VIEWPORT, BROWSER_ARGS

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

# ========== 配置 ==========

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_PER_URL = 30
SCROLL_ROUNDS = 50
SCROLL_WAIT_MS = 1200
NO_CHANGE_THRESHOLD = 5

# 14个链接列表
URL_LIST = [
    ("https://www.zhihu.com/question/65384083/answer/73753437178", "问题回答"),
    ("https://zhuanlan.zhihu.com/p/367465492", "专栏文章"),
    ("https://zhuanlan.zhihu.com/p/711729783", "专栏文章"),
    ("https://zhuanlan.zhihu.com/p/689851290", "专栏文章"),
    ("https://zhuanlan.zhihu.com/p/16907679481", "专栏文章"),
    ("https://zhuanlan.zhihu.com/p/711445160", "专栏文章"),
    ("https://zhuanlan.zhihu.com/p/690681361", "专栏文章"),
    ("https://www.zhihu.com/question/65384083/answer/460443655", "问题回答"),
    ("https://www.zhihu.com/question/585941568/answer/2908321967", "问题回答"),
    ("https://zhuanlan.zhihu.com/p/24254194796", "专栏文章"),
    ("https://www.zhihu.com/question/585941696/answer/2908330132", "问题回答"),
    ("https://www.zhihu.com/question/585941610/answer/2908341281", "问题回答"),
    ("https://www.zhihu.com/question/65384083/answer/1384194481", "问题回答"),
    ("https://www.zhihu.com/question/65384083/answer/472983682", "问题回答"),
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("batch_scraper")


def log(msg: str):
    print(f"  {msg}")
    logger.info(msg)


# ========== 反检测JS ==========

ANTI_DETECTION_JS = f"""() => {{
{STEALTH_JS}
}}"""


# ========== 提取问题回答 ==========

EXTRACT_ANSWERS_JS = """
() => {
    const results = [];
    const seen = new Set();
    const containers = Array.from(document.querySelectorAll('.ContentItem.AnswerItem, .AnswerCard'));
    containers.forEach(el => {
        const nameEl = el.querySelector('.AuthorInfo-name, [class*="AuthorInfo-name"]');
        const name = nameEl ? nameEl.innerText.trim() : '';
        const headlineEl = el.querySelector('.AuthorInfo-headline, [class*="AuthorInfo-headline"]');
        const headline = headlineEl ? headlineEl.innerText.trim() : '';
        const badgeEl = el.querySelector('.AuthorInfo-badgeText, [class*="AuthorInfo-badge"]');
        const badge = badgeEl ? badgeEl.innerText.trim() : '';
        let content = '';
        for (const sel of ['.RichContent-inner','.RichText','.CopyrightRichText-richText','[class*="RichContent-inner"]']) {
            const el2 = el.querySelector(sel);
            if (el2) { content = el2.innerText.trim(); break; }
        }
        const timeEl = el.querySelector('.ContentItem-time, [class*="ContentItem-time"]');
        const publish_time = timeEl ? timeEl.innerText.trim() : '';
        let upvotes = 0;
        const voteBtn = el.querySelector('.VoteButton, [class*="VoteButton"]');
        if (voteBtn) {
            const m = (voteBtn.innerText || '').match(/赞同\\s*(\\d+)/);
            if (m) upvotes = parseInt(m[1], 10);
        }
        let comments = 0;
        el.querySelectorAll('.ContentItem-action, [class*="ContentItem-action"]').forEach(a => {
            const m = (a.innerText || '').match(/评论\\s*(\\d+)/);
            if (m) comments = parseInt(m[1], 10);
        });
        let isRecommended = false;
        if ((el.innerText || '').includes('推荐回答') || (el.innerText || '').includes('精选回答')) isRecommended = true;
        const key = (name + '|' + content.slice(0, 50)).trim();
        if (key && !seen.has(key) && content.length > 0) {
            seen.add(key);
            results.push({name, headline, badge, content, publish_time, upvotes, comments, isRecommended});
        }
    });
    return results;
}
"""


# ========== 提取专栏文章 ==========

EXTRACT_ZHUANLAN_JS = """
() => {
    const results = [];
    // 文章标题
    const titleEl = document.querySelector('h1, .Post-Title, [class*="Title"], .RichContent h1');
    const title = titleEl ? titleEl.innerText.trim() : '';
    // 作者信息
    const authorEl = document.querySelector('.AuthorInfo-name, [class*="author"] [class*="name"], .Popover a');
    let name = '';
    if (authorEl) name = authorEl.innerText.trim();
    // 如果找不到，尝试其他选择器
    if (!name) {
        const alt = document.querySelector('[class*="AuthorInfo"] span, [class*="author"]');
        if (alt) name = alt.innerText.trim();
    }
    // 作者简介
    const headlineEl = document.querySelector('.AuthorInfo-headline, [class*="author"] [class*="description"]');
    const headline = headlineEl ? headlineEl.innerText.trim() : '';
    // 文章内容
    let content = '';
    for (const sel of ['.RichText', '.Post-RichTextContainer', '[class*="RichText"]', '.RichContent']) {
        const el = document.querySelector(sel);
        if (el && el.innerText.trim().length > 50) {
            content = el.innerText.trim();
            break;
        }
    }
    // 发布时间
    const timeEl = document.querySelector('.ContentItem-time, [class*="ContentItem-time"], time, [datetime]');
    let publish_time = '';
    if (timeEl) {
        publish_time = timeEl.innerText.trim() || timeEl.getAttribute('datetime') || '';
    }
    // 赞同数（专栏文章的赞同）
    let upvotes = 0;
    const voteEls = document.querySelectorAll('button, [class*="VoteButton"], [class*="vote"]');
    for (const btn of voteEls) {
        const text = btn.innerText || btn.textContent || '';
        const m = text.match(/(\\d+)\\s*赞同/);
        if (m) { upvotes = parseInt(m[1], 10); break; }
        const m2 = text.match(/赞同\\s*(\\d+)/);
        if (m2) { upvotes = parseInt(m2[1], 10); break; }
    }
    // 评论数
    let comments = 0;
    const commentEls = document.querySelectorAll('button, [class*="comment"], [class*="Comment"]');
    for (const btn of commentEls) {
        const text = btn.innerText || btn.textContent || '';
        const m = text.match(/(\\d+)\\s*条评论/);
        if (m) { comments = parseInt(m[1], 10); break; }
        const m2 = text.match(/评论\\s*(\\d+)/);
        if (m2) { comments = parseInt(m2[1], 10); break; }
    }
    if (title || content) {
        results.push({
            name: name || '未知作者',
            headline: headline,
            badge: '',
            content: content || title,
            publish_time: publish_time,
            upvotes: upvotes,
            comments: comments,
            isRecommended: false,
        });
    }
    return results;
}
"""


# ========== 浏览器配置 ==========

def create_browser_context(p, profile_dir: str):
    return p.chromium.launch_persistent_context(
        profile_dir,
        headless=False,
        args=BROWSER_ARGS + [
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-size=1280,900",
        ],
        viewport={"width": 1280, "height": 900},
        user_agent=DEFAULT_USER_AGENT,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        bypass_csp=True,
    )


# ========== 爬取单个URL ==========

def scrape_single_url(page, url: str, page_type: str, max_items: int) -> List[Dict[str, Any]]:
    """爬取单个URL，返回数据列表"""
    log(f"\n📄 正在加载: {url[:60]}...")
    page.goto(url, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    page.wait_for_timeout(1000)

    all_data = []
    seen_keys = set()

    # 检测是否需要登录
    if "login" in page.url.lower() or page.locator("input[type='password']").count() > 0:
        log("🔑 需要登录，请在浏览器中手动登录...")
        waited = 0
        while waited < 300:
            page.wait_for_timeout(2000)
            waited += 2
            if "login" not in page.url.lower() and page.locator("input[type='password']").count() == 0:
                log("✅ 已登录")
                page.wait_for_timeout(3000)
                break
            if waited % 10 == 0:
                log(f"   ... 等待中 ({waited}s)")

    if page_type == "专栏文章":
        # 专栏文章：直接提取，无需滚动
        log("   📝 专栏文章模式")
        data = page.evaluate(EXTRACT_ZHUANLAN_JS)
        for item in data:
            key = (item.get("name", "") + "|" + item.get("content", "")[:50]).strip()
            if key and key not in seen_keys and item.get("content"):
                seen_keys.add(key)
                all_data.append(item)
        page.wait_for_timeout(2000)
    else:
        # 问题回答：尝试点击"查看全部" + 滚动加载
        log("   💬 问题回答模式")
        try:
            view_all = page.locator("text=查看全部").first
            if view_all.is_visible(timeout=5000):
                log("   🖱️ 点击'查看全部回答'...")
                view_all.click()
                page.wait_for_timeout(5000)
        except Exception:
            pass

        page.wait_for_timeout(3000)

        # 滚动加载
        last_count = 0
        no_change = 0
        for rnd in range(SCROLL_ROUNDS):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(SCROLL_WAIT_MS)

            # 展开阅读全文
            try:
                btns = page.locator("button:has-text('阅读全文'), text=展开").all()
                for btn in btns[:5]:
                    try:
                        if btn.is_visible(timeout=500):
                            btn.click(timeout=1000)
                            page.wait_for_timeout(800)
                    except Exception:
                        pass
            except Exception:
                pass

            data = page.evaluate(EXTRACT_ANSWERS_JS)
            for item in data:
                key = (item.get("name", "") + "|" + item.get("content", "")[:50]).strip()
                if key and key not in seen_keys and item.get("content"):
                    seen_keys.add(key)
                    all_data.append(item)

            cur = len(all_data)
            if cur == last_count:
                no_change += 1
                if no_change >= NO_CHANGE_THRESHOLD:
                    log(f"   ✓ 连续{NO_CHANGE_THRESHOLD}轮无新数据，停止")
                    break
            else:
                no_change = 0
                if rnd % 3 == 0:
                    log(f"   ... 当前 {cur} 条")
            last_count = cur
            if cur >= max_items:
                log(f"   ✓ 已达上限 {max_items} 条")
                break

    log(f"   ✅ 提取到 {len(all_data)} 条数据")
    return all_data


# ========== 保存合并Excel ==========

def save_merged_excel(all_data: List[Dict[str, Any]], filepath: str):
    """保存所有数据到一个Excel"""
    log(f"📊 正在生成合并Excel: {filepath}")
    wb = Workbook()
    ws = wb.active
    ws.title = "知乎批量采集"

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

    headers = [
        "总序号", "来源链接", "页面类型",
        "回答者昵称", "回答者简介", "认证信息",
        "内容", "发布时间", "赞同数", "评论数", "是否推荐",
    ]
    widths = [8, 50, 12, 18, 25, 20, 80, 18, 10, 10, 12]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font, cell.fill, cell.alignment, cell.border = header_font, header_fill, header_align, thin_border
        ws.column_dimensions[chr(64 + col)].width = w

    for i, item in enumerate(all_data, 1):
        row_data = [
            i,
            item.get("source_url", ""),
            item.get("page_type", ""),
            item.get("name", ""),
            item.get("headline", ""),
            item.get("badge", ""),
            item.get("content", ""),
            item.get("publish_time", ""),
            item.get("upvotes", 0),
            item.get("comments", 0),
            "是" if item.get("isRecommended") else "否",
        ]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=i + 1, column=col, value=val)
            cell.font, cell.border = data_font, thin_border
            cell.alignment = data_align if col == 7 else center_align

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:K{len(all_data) + 1}"
    wb.save(filepath)
    log(f"   ✅ Excel已保存: {filepath}")


# ========== 主程序 ==========

def main():
    print(f"\n{'='*70}")
    print(f"  知乎批量爬取脚本")
    print(f"  共 {len(URL_LIST)} 个链接")
    print(f"{'='*70}\n")

    all_results = []
    profile_dir = os.path.join(SCRIPT_DIR, "browser_profile")
    os.makedirs(profile_dir, exist_ok=True)

    with sync_playwright() as p:
        # 安装浏览器
        import subprocess
        r = subprocess.run([sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
                           capture_output=True, text=True)
        if "already" not in r.stdout and "already" not in r.stderr:
            log("⚠️ 安装 Playwright Chromium...")
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            log("✅ 完成")

        context = create_browser_context(p, profile_dir)
        page = context.new_page()
        page.add_init_script(STEALTH_JS)

        try:
            for idx, (url, page_type) in enumerate(URL_LIST, 1):
                print(f"\n{'─'*70}")
                print(f"  [{idx}/{len(URL_LIST)}] {page_type}")
                print(f"  {url}")
                print(f"{'─'*70}")

                try:
                    data = scrape_single_url(page, url, page_type, MAX_PER_URL)
                    for item in data:
                        item["source_url"] = url
                        item["page_type"] = page_type
                    all_results.extend(data)
                    log(f"   📊 累计: {len(all_results)} 条")
                except Exception as e:
                    log(f"   ❌ 爬取失败: {e}")
                    import traceback
                    traceback.print_exc()

        finally:
            context.close()
            log("🔒 浏览器已关闭")

    # 最终去重
    seen = set()
    unique = []
    for item in all_results:
        key = (item.get("source_url", "") + "|" + item.get("name", "") + "|" + item.get("content", "")[:50]).strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    # 排序：按赞同数降序
    unique.sort(key=lambda x: x.get("upvotes", 0), reverse=True)

    log(f"\n📦 最终去重后: {len(unique)} 条")

    if not unique:
        print(f"\n{'='*70}")
        print(f"  ⚠️ 未获取到任何数据")
        print(f"{'='*70}\n")
        return

    # 保存
    ts = time.strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, f"zhihu_batch_{ts}.xlsx")
    save_merged_excel(unique, output_path)

    # 统计
    stats = {}
    for item in unique:
        src = item.get("source_url", "未知")
        stats[src] = stats.get(src, 0) + 1

    print(f"\n{'='*70}")
    print(f"  ✅ 批量爬取完成")
    print(f"  总数据条数: {len(unique)}")
    print(f"\n  各链接统计:")
    for url, count in stats.items():
        short = url.replace("https://", "").replace("www.", "").replace("zhuanlan.", "")[:40]
        print(f"    {short}... : {count} 条")
    print(f"\n  📊 输出文件: {output_path}")
    print(f"{'='*70}\n")

    return output_path


if __name__ == "__main__":
    main()
