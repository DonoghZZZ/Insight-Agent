#!/usr/bin/env python3
"""
小红书笔记爬虫 v2 — 先登录再爬取，完整评论区加载

核心流程:
  1. 打开浏览器 → 小红书首页
  2. 等待用户手动登录（扫码/手机号）
  3. 验证登录态
  4. 导航到目标笔记URL
  5. 提取帖子信息 + 滚动加载全部评论
  6. 导出Excel

用法:
  python3 xiaohongshu_scraper.py <小红书笔记URL>
  python3 xiaohongshu_scraper.py --max-comments 200
  python3 xiaohongshu_scraper.py --local <本地HTML路径>
"""

import sys
import os
import re
import time
import json
import random
import shutil
import logging
import argparse
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.browser import STEALTH_JS, DEFAULT_USER_AGENT, DEFAULT_VIEWPORT, BROWSER_ARGS
from common.login_helper import (
    ensure_session, get_smart_headless, is_session_valid,
    mark_session_valid, XHS_CHECK_LOGIN_JS,
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
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "xhs_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

XHS_HOME = "https://www.xiaohongshu.com"
DEFAULT_URL = "https://www.xiaohongshu.com/explore/69f090df000000001a02c6b3?xsec_token=ABN5nhBgLgONk84VyAbXBS8Pu_caFBwRfcHmR9T_gF9Yc=&xsec_source="
MAX_COMMENTS = 200
SCROLL_ROUNDS = 80
SCROLL_WAIT_MS = 1500
NO_CHANGE_THRESHOLD = 8
RETRY_TIMES = 3
NOTE_NAV_RETRY = 4
NOTE_NAV_RETRY_WAIT_MS = 3000
LOGIN_TIMEOUT = 300  # 秒

# ========== 日志配置 ==========

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("xhs_scraper")


def log(msg: str, level: str = "info"):
    if level == "info":
        logger.info(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)


# ========== 命令行参数 ==========

def parse_args():
    parser = argparse.ArgumentParser(
        description="小红书笔记爬虫 v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 xiaohongshu_scraper.py <URL>
  python3 xiaohongshu_scraper.py --max-comments 300
  python3 xiaohongshu_scraper.py --local /path/to/note.html
        """,
    )
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="目标小红书笔记URL")
    parser.add_argument("--urls-file", dest="urls_file", default=None, help="批量爬取：URL列表文件（每行一个）")
    parser.add_argument("--max-comments", type=int, default=MAX_COMMENTS, help=f"最多爬取评论数（默认: {MAX_COMMENTS}）")
    parser.add_argument("--local", dest="local_file", default=None, help="解析本地HTML文件路径")
    parser.add_argument("--output", dest="output_file", default=None, help="指定输出Excel文件路径")
    parser.add_argument("--clear-profile", action="store_true", default=False, help="清除浏览器缓存/登录态重新开始")
    parser.add_argument("--headless", action="store_true", default=False, help="无头模式运行浏览器")
    parser.add_argument("--login-only", dest="login_only", action="store_true", default=False,
                        help="仅打开浏览器登录，登录成功后退出（用于首次配置）")
    return parser.parse_args()


# ========== 浏览器配置 ==========

def create_browser_context(p, headless=False):
    """创建持久化浏览器上下文，保留登录态"""
    profile_dir = os.path.join(SCRIPT_DIR, "xhs_browser_profile")

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


# ========== 浏览器端JS: 提取帖子信息 ==========

EXTRACT_NOTE_JS = """
() => {
    const result = {};

    // 策略1: 从 meta 标签提取元数据
    function getMeta(name) {
        const el = document.querySelector('meta[name="' + name + '"], meta[property="' + name + '"]');
        return el ? el.getAttribute('content') : '';
    }
    result.title = getMeta('og:title').replace(/ - 小红书$/, '').replace(/^\\s+|\\s+$/g, '');
    result.liked_count = getMeta('og:xhs:note_like');
    result.collected_count = getMeta('og:xhs:note_collect');
    result.comment_count = getMeta('og:xhs:note_comment');
    result.share_count = '';

    // 策略2: 从 JSON-LD 提取
    try {
        const ldJsons = document.querySelectorAll('script[type="application/ld+json"]');
        ldJsons.forEach(s => {
            try {
                const data = JSON.parse(s.textContent);
                if (data['@type'] === 'Article' || data['@type'] === 'SocialMediaPosting') {
                    if (!result.title && data.headline) result.title = data.headline;
                    if (data.author) {
                        if (!result.author && data.author.name) result.author = data.author.name;
                        if (!result.author_id && data.author.url) {
                            const m = data.author.url.match(/\\/user\\/profile\\/([^?]+)/);
                            if (m) result.author_id = m[1];
                        }
                    }
                    if (!result.content && data.articleBody) result.content = data.articleBody;
                    if (data.datePublished && !result.publish_time) result.publish_time = data.datePublished;
                }
            } catch(e) {}
        });
    } catch(e) {}

    // 策略3: window.__INITIAL_STATE__ (兼容多种路径)
    try {
        const state = window.__INITIAL_STATE__;
        if (state) {
            // 路径 A: state.note (旧版)
            let note = state.note;
            // 路径 B: state.noteDetailMap (新版)
            if (!note && state.noteDetailMap) {
                const noteIds = Object.keys(state.noteDetailMap);
                if (noteIds.length > 0) {
                    note = state.noteDetailMap[noteIds[noteIds.length - 1]];
                    if (note && note.note) note = note.note;
                }
            }
            // 路径 C: state.note.noteDetailMap
            if (!note && state.note && state.note.noteDetailMap) {
                const noteIds = Object.keys(state.note.noteDetailMap);
                if (noteIds.length > 0) {
                    const nd = state.note.noteDetailMap[noteIds[noteIds.length - 1]];
                    if (nd && nd.note) note = nd.note;
                }
            }

            if (note) {
                if (!result.title && note.title) result.title = note.title;
                if (!result.content && note.desc) result.content = note.desc;
                if (note.interact_info || note.interactInfo) {
                    const ii = note.interact_info || note.interactInfo || {};
                    if (!result.liked_count && ii.liked_count !== undefined) result.liked_count = String(ii.liked_count);
                    if (!result.liked_count && ii.likedCount !== undefined) result.liked_count = String(ii.likedCount);
                    if (!result.collected_count && ii.collected_count !== undefined) result.collected_count = String(ii.collected_count);
                    if (!result.collected_count && ii.collectedCount !== undefined) result.collected_count = String(ii.collectedCount);
                    if (!result.comment_count && ii.comment_count !== undefined) result.comment_count = String(ii.comment_count);
                    if (!result.comment_count && ii.commentCount !== undefined) result.comment_count = String(ii.commentCount);
                    if (!result.share_count && ii.share_count !== undefined) result.share_count = String(ii.share_count);
                    if (!result.share_count && ii.shareCount !== undefined) result.share_count = String(ii.shareCount);
                }
                if (note.user) {
                    if (!result.author && note.user.nickname) result.author = note.user.nickname;
                    if (!result.author && note.user.nick_name) result.author = note.user.nick_name;
                    if (!result.author_id && note.user.user_id) result.author_id = String(note.user.user_id);
                    if (!result.author_id && note.user.userId) result.author_id = String(note.user.userId);
                    if (!result.author_id && note.user.id) result.author_id = String(note.user.id);
                }
                if (note.tag_list && note.tag_list.length) {
                    result.tags = note.tag_list.map(t => t.name || t.tag_name || t.tagName || '').filter(Boolean);
                }
                if (note.time && !result.publish_time) result.publish_time = String(note.time);
                if (note.create_time && !result.publish_time) result.publish_time = String(note.create_time);
                if (note.createTime && !result.publish_time) result.publish_time = String(note.createTime);
                if (note.note_id && !result.note_id) result.note_id = note.note_id;
            }
        }
    } catch(e) {}

    // 策略4: 从 #__NEXT_DATA__ 提取（Next.js SSR）
    try {
        const nextDataEl = document.getElementById('__NEXT_DATA__');
        if (nextDataEl) {
            const nextData = JSON.parse(nextDataEl.textContent);
            const props = nextData?.props?.pageProps;
            if (props) {
                const noteData = props.noteDetail || props.note || props.detail || props;
                if (noteData) {
                    const nd = noteData.note || noteData.noteDetail || noteData;
                    if (!result.title && nd.title) result.title = nd.title;
                    if (!result.content && nd.desc) result.content = nd.desc;
                    if (!result.note_id && nd.noteId) result.note_id = nd.noteId;
                }
                if (props.interactInfo && !result.liked_count) {
                    const ii = props.interactInfo;
                    if (ii.likedCount) result.liked_count = String(ii.likedCount);
                    if (ii.collectedCount) result.collected_count = String(ii.collectedCount);
                    if (ii.commentCount) result.comment_count = String(ii.commentCount);
                    if (ii.shareCount) result.share_count = String(ii.shareCount);
                }
            }
        }
    } catch(e) {}

    // 策略5: DOM 选择器兜底（更广泛的匹配）
    if (!result.title) {
        for (const sel of [
            '#detail-title', '.note-content .title', '.title', 'h1',
            '[class*="title"]', '[data-v-72661160] .title',
        ]) {
            const el = document.querySelector(sel);
            if (el && el.innerText && el.innerText.trim().length > 1) {
                result.title = el.innerText.trim();
                break;
            }
        }
    }

    if (!result.author) {
        for (const sel of [
            '.author-wrapper .username', 'a.name', '.author-info .name',
            '.username', '[class*="username"]', '[class*="author"] [class*="name"]',
            '.nickname', '.nick-name',
        ]) {
            const el = document.querySelector(sel);
            if (el && el.innerText && el.innerText.trim().length > 0) {
                result.author = el.innerText.trim();
                break;
            }
        }
    }

    if (!result.author_id) {
        const authorLink = document.querySelector('a[href*="/user/profile/"], a[href*="/profile/"], a[href*="user_id="]');
        if (authorLink) {
            const href = authorLink.getAttribute('href') || '';
            let m = href.match(/\\/user\\/profile\\/([^?]+)/);
            if (!m) m = href.match(/\\/profile\\/([^?]+)/);
            if (!m) m = href.match(/user_id=([^&]+)/);
            result.author_id = m ? m[1] : '';
        }
    }

    if (!result.tags || !result.tags.length) {
        const tags = [];
        document.querySelectorAll(
            '.note-content .tag, a[href*="/search_result/"], a[href*="/topics/"], ' +
            '[class*="tag"], .hash-tag, [data-v-72661160] .tag, ' +
            '[class*="hash_tag"]'
        ).forEach(el => {
            const text = (el.innerText || '').trim().replace(/^#/, '');
            if (text && text.length > 1 && text.length < 50) tags.push(text);
        });
        result.tags = [...new Set(tags)];
    }

    if (!result.content) {
        for (const sel of [
            '.note-content .desc', '#detail-desc .note-text', '.note-scroller .desc',
            '.desc', '.note-text', '[class*="desc"]', '[class*="note-text"]',
            '.note-scroller .note-content', '#detail-desc',
        ]) {
            const el = document.querySelector(sel);
            const text = el ? (el.innerText || '').trim() : '';
            if (text.length > 10) {
                result.content = text;
                break;
            }
        }
    }

    if (!result.publish_time) {
        for (const sel of [
            '.note-content .date', '.bottom-container .date', '.date-container',
            '.date', '[class*="date"]', '.bottom-container time', 'time',
            '.publish-date', '.publish-time',
        ]) {
            const el = document.querySelector(sel);
            if (el && el.innerText && el.innerText.trim().length > 3) {
                result.publish_time = el.innerText.trim();
                break;
            }
        }
    }

    // 互动数据 DOM 兜底
    if (!result.liked_count || !result.collected_count || !result.comment_count) {
        const interactBar = document.querySelector(
            '.interactions, .engage-bar, .interact-container, ' +
            '[class*="interact"], [class*="engage"], [class*="action-bar"]'
        );
        if (interactBar) {
            const txt = interactBar.innerText;
            const lk = txt.match(/([\\d,.万]+)\\s*[赞]/);
            if (lk && !result.liked_count) result.liked_count = lk[1];
            const ck = txt.match(/([\\d,.万]+)\\s*[收藏]/);
            if (ck && !result.collected_count) result.collected_count = ck[1];
            const mk = txt.match(/([\\d,.万]+)\\s*[评论]/);
            if (mk && !result.comment_count) result.comment_count = mk[1];
            const sk = txt.match(/([\\d,.万]+)\\s*[分享]/);
            if (sk && !result.share_count) result.share_count = sk[1];
        }
    }

    // URL / note_id
    if (!result.note_id) {
        const urlMatch = window.location.href.match(/\\/(explore|discovery\\/item)\\/([a-f0-9]+)/);
        if (urlMatch) result.note_id = urlMatch[2] || urlMatch[1];
    }

    // 确保所有字段有值
    result.title = result.title || '';
    result.author = result.author || '';
    result.author_id = String(result.author_id || '');
    result.note_id = String(result.note_id || '');
    result.publish_time = result.publish_time || '';
    result.liked_count = String(result.liked_count || '');
    result.collected_count = String(result.collected_count || '');
    result.comment_count = String(result.comment_count || '');
    result.share_count = String(result.share_count || '');
    result.tags = result.tags || [];
    result.content = result.content || '';

    return result;
}
"""


# ========== 浏览器端JS: 检测笔记是否成功加载 ==========

CHECK_NOTE_LOADED_JS = """
() => {
    const result = {loaded: false, reason: '', details: {}};

    const bodyText = (document.body ? document.body.innerText : '').trim();

    // 反爬/错误页面关键词检测
    const errorKeywords = [
        '笔记不见了', '内容不存在', '该笔记暂时无法浏览',
        '笔记正在审核中', '请稍后再试', '页面不存在', '内容已删除',
        'error', 'Blocked', 'forbidden', 'captcha', '验证码',
        '人机验证', '滑动验证', '安全验证',
    ];
    for (const kw of errorKeywords) {
        if (bodyText.includes(kw)) {
            result.reason = '检测到反爬/错误页面: ' + kw;
            result.details.error_keyword = kw;
            return result;
        }
    }

    // 空白页检测：body 内容极短
    if (bodyText.length < 80) {
        result.reason = '页面内容过短(' + bodyText.length + '字符)，疑似空白页';
        result.details.body_length = bodyText.length;
        return result;
    }

    // 成功加载指标检测
    const hasTitle = !!document.querySelector('#detail-title, .title, h1, [class*="title"]');
    const hasNoteScroller = !!document.querySelector('.note-scroller');
    const hasInteractBar = !!document.querySelector('.interactions, .engage-bar, .interact-container, [class*="interact"]');
    const hasComment = !!document.querySelector('.comment-item, [class*="comment-item"]');

    result.details = {hasTitle, hasNoteScroller, hasInteractBar, hasComment};

    if (hasTitle && (hasNoteScroller || hasInteractBar || hasComment)) {
        result.loaded = true;
        result.reason = '检测到标题和内容容器，笔记加载成功';
    } else if (hasNoteScroller || hasInteractBar) {
        result.loaded = true;
        result.reason = '检测到内容容器，笔记可能已加载';
    } else {
        result.reason = '未检测到笔记核心元素';
    }

    return result;
}
"""


# ========== 浏览器端JS: 提取评论 ==========

EXTRACT_COMMENTS_JS = """
() => {
    const results = [];
    const seen = new Set();

    // 精准选择器：小红书 PC 端评论区结构
    const commentItems = document.querySelectorAll(
        '.comment-item:not(.comment-item-placeholder)'
    );

    commentItems.forEach(el => {
        const commentId = el.id || '';

        // 用户名：a.name
        const nameEl = el.querySelector('a.name');
        const username = nameEl ? nameEl.innerText.trim() : '';

        // 用户ID：a[data-user-id]
        const userLink = el.querySelector('a[data-user-id]');
        const userId = userLink ? userLink.getAttribute('data-user-id') : '';

        // 用户标签：span.tag（如"作者"）
        const userTags = [];
        el.querySelectorAll('span.tag').forEach(t => {
            const text = t.innerText.trim();
            if (text && text.length < 10) userTags.push(text);
        });
        const userTagsStr = [...new Set(userTags)].join(',');

        // 评论内容：.note-text
        const noteTextEl = el.querySelector('.note-text');
        let content = noteTextEl ? noteTextEl.innerText.trim() : '';
        if (!content) {
            const contentEl = el.querySelector('.content');
            if (contentEl) content = contentEl.innerText.trim();
        }

        // 日期和位置：.date 下的 span
        let date = '', location = '';
        const dateEl = el.querySelector('.date');
        if (dateEl) {
            const spans = dateEl.querySelectorAll(':scope > span');
            if (spans.length >= 1) date = spans[0].innerText.trim();
            if (spans.length >= 2) location = spans[1].innerText.trim();
            if (!location) {
                const locEl = dateEl.querySelector('.location');
                if (locEl) location = locEl.innerText.trim();
            }
        }

        // 点赞数：.like-wrapper .count
        let likes = '';
        const countEl = el.querySelector('.like-wrapper .count');
        if (countEl) {
            const countText = countEl.innerText.trim();
            const m = countText.match(/(\\d+)/);
            if (m) {
                likes = m[1];
            } else {
                likes = countText;  // 保留原始值如"赞"
            }
        }

        // 是否为子评论（回复）
        const isSub = el.classList.contains('comment-item-sub');

        const key = (username + '|' + content.slice(0, 40)).trim();
        if (key && !seen.has(key) && content.length > 0) {
            seen.add(key);
            results.push({
                comment_id: commentId,
                username: username,
                user_id: userId,
                user_tags: userTagsStr,
                content: content,
                date: date,
                location: location,
                likes: likes,
                is_sub: isSub,
            });
        }
    });

    return results;
}
"""


# ========== 检查登录态 JS ==========

CHECK_LOGIN_JS = """
() => {
    // 检查多个登录态指标
    const checks = {};
    
    // 1. 检查是否有用户头像/昵称（已登录标志）
    const loginBtn = document.querySelector('.login-btn, .sign-in, [class*="login-btn"]');
    checks.has_login_btn = !!loginBtn;
    
    // 2. 检查cookie中是否有登录相关key
    checks.has_userid_cookie = document.cookie.includes('web_session') || 
                                document.cookie.includes('a1');
    
    // 3. 检查URL是否已不在login页
    checks.url_has_login = window.location.href.includes('/login');
    
    // 4. 检查页面是否有user相关元素
    const userEl = document.querySelector('.user, .avatar-container, .side-bar-user, [class*="user-info"]');
    checks.has_user_element = !!userEl;
    
    // 登录态判断：不在login页 且 （有用户元素 或 有登录cookie）
    checks.is_logged_in = !checks.url_has_login && 
                          (checks.has_user_element || checks.has_userid_cookie);

    return checks;
}
"""


# ========== 登录流程 ==========

def ensure_login(page) -> bool:
    """
    打开小红书首页，暂停等待用户手动登录，用户确认后继续。
    流程：导航到首页 → 检测 session → 未登录则提示用户登录 → 继续
    """
    log("=" * 60)
    log("🔑 === 登录阶段 ===")
    log("=" * 60)

    # 使用统一的 session 管理
    return ensure_session(page, "xiaohongshu")


# ========== 本地HTML解析 ==========

def parse_local_html(file_path: str) -> Tuple[Dict, List[Dict]]:
    log(f"📄 解析本地HTML文件: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    note_info = {"title": "", "author": "", "author_id": "", "content": "", "tags": [],
                 "liked_count": "", "collected_count": "", "comment_count": "",
                 "share_count": "", "publish_time": "", "note_id": ""}

    title_tag = soup.find("title")
    if title_tag:
        note_info["title"] = title_tag.text.strip().replace(" - 小红书", "")

    desc_matches = re.findall(r'"desc":"(.+?)"', html)
    for m in desc_matches:
        decoded = m.replace('\\n', '\n').replace('\\t', '\t')
        if len(decoded) > 50:
            note_info["content"] = decoded
            break

    if note_info["content"]:
        note_info["tags"] = re.findall(r'#([\u4e00-\u9fa5\w]+)', note_info["content"])

    interact_match = re.search(r'"interactInfo":\s*\{([^}]+)\}', html)
    if interact_match:
        for key in ["likedCount", "collectedCount", "commentCount", "shareCount"]:
            m = re.search(rf'"{key}":\s*"([^"]*)"', interact_match.group(1))
            if m:
                note_info[key.lower().replace("count", "_count")] = m.group(1)

    comment_match = re.search(r'(\d+)\s*条评论', html)
    if comment_match and not note_info["comment_count"]:
        note_info["comment_count"] = comment_match.group(1)

    comments = []
    comment_items = soup.find_all("div", class_=re.compile("comment-item"))
    seen = set()

    for el in comment_items:
        name = el.find("a", class_="name")
        username = name.text.strip() if name else ""
        user_id = name.get("data-user-id", "") if name else ""

        tags_list = []
        for t in el.find_all("span", class_="tag"):
            if t.text.strip(): tags_list.append(t.text.strip())
        for t in el.find_all("span", class_=re.compile("top")):
            if t.text.strip(): tags_list.append(t.text.strip())
        user_tags = ",".join(tags_list)

        content_div = el.find("div", class_="content")
        content = content_div.get_text(separator=" ", strip=True) if content_div else ""

        date_div = el.find("div", class_="date")
        date_text, location = "", ""
        if date_div:
            spans = date_div.find_all("span")
            for i, s in enumerate(spans):
                text = s.get_text(strip=True)
                if text:
                    if i == 0: date_text = text
                    else: location = text

        likes = ""
        like_wrapper = el.find("span", class_=re.compile("like-wrapper"))
        if like_wrapper:
            count_span = like_wrapper.find("span", class_="count")
            if count_span:
                ct = count_span.text.strip()
                if ct and ct != "赞": likes = ct

        is_sub = "comment-item-sub" in " ".join(el.get("class", []))

        key = (username + "|" + content[:40]).strip()
        if key and key not in seen and content:
            seen.add(key)
            comments.append({
                "comment_id": el.get("id", ""),
                "username": username, "user_id": user_id,
                "user_tags": user_tags, "content": content,
                "date": date_text, "location": location,
                "likes": likes, "is_sub": is_sub,
            })

    log(f"   ✅ 帖子信息 + {len(comments)} 条评论")
    return note_info, comments


# ========== Playwright 爬取 ==========

def scrape_with_playwright(url: str, max_comments: int = MAX_COMMENTS, clear_profile: bool = False, headless: bool = False, login_only: bool = False):
    """先登录再爬取小红书笔记"""

    # 智能决定是否 headless（有缓存 session 则 headless，否则弹浏览器登录）
    headless = get_smart_headless("xiaohongshu", headless)

    if clear_profile:
        profile_dir = os.path.join(SCRIPT_DIR, "xhs_browser_profile")
        if os.path.exists(profile_dir):
            log(f"🗑️ 清除浏览器缓存: {profile_dir}")
            shutil.rmtree(profile_dir)

    all_comments = []
    seen_keys = set()
    note_info = {}

    with sync_playwright() as p:
        # 检查浏览器
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True,
        )
        if "already" not in r.stdout and "already" not in r.stderr:
            log("⚠️ 安装 Playwright Chromium...")
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

        context = create_browser_context(p, headless=headless)
        page = context.new_page()
        page.add_init_script(STEALTH_JS)

        try:
            # ===== 阶段1: 登录 =====
            logged_in = ensure_login(page)
            if not logged_in:
                log("❌ 用户未确认登录，退出", level="error")
                return {}, []

            # login-only 模式：登录完成就退出
            if login_only:
                log("✅ 登录模式完成")
                context.close()
                return {}, []

            # ===== 阶段2: 导航到目标笔记（带反爬重试） =====
            log("=" * 60)
            log("📄 === 数据抓取阶段 ===")
            log(f"📌 目标URL: {url}")
            log("=" * 60)

            note_loaded = False
            for nav_attempt in range(1, NOTE_NAV_RETRY + 1):
                log(f"⏳ 第{nav_attempt}次加载笔记页面...")
                page.goto(url, timeout=60000, wait_until="domcontentloaded")

                page.wait_for_timeout(5000)
                page.wait_for_timeout(1000)

                check_result = page.evaluate(CHECK_NOTE_LOADED_JS)
                details = check_result.get('details', {})
                log(f"   检测结果: loaded={check_result.get('loaded')}, "
                    f"reason={check_result.get('reason', '')[:60]}, "
                    f"details={details}")

                if check_result.get('loaded'):
                    note_loaded = True
                    log(f"   ✅ 笔记页面加载成功")
                    break
                else:
                    reason = check_result.get('reason', '未知原因')
                    if nav_attempt < NOTE_NAV_RETRY:
                        log(f"   ⚠️ 笔记未成功加载({reason})，{NOTE_NAV_RETRY_WAIT_MS / 1000:.0f}秒后重试...")
                        page.wait_for_timeout(NOTE_NAV_RETRY_WAIT_MS)
                    else:
                        log(f"   ❌ 已重试{NOTE_NAV_RETRY}次，笔记仍未加载({reason})，尝试继续...", level="warning")

            # 等待页面关键元素
            if note_loaded:
                try:
                    page.wait_for_selector("#detail-title, .title, h1", timeout=5000)
                except PwTimeout:
                    log("⚠️ 等待标题元素超时", level="warning")

            # ===== 阶段3: 提取帖子信息 =====
            log("📝 提取帖子信息...")
            note_info = page.evaluate(EXTRACT_NOTE_JS)
            log(f"   标题: {note_info.get('title', 'N/A')[:50]}")
            log(f"   作者: {note_info.get('author', 'N/A')}")
            log(f"   标签: {', '.join(note_info.get('tags', []))}")
            log(f"   点赞: {note_info.get('liked_count', '?')} | "
                f"收藏: {note_info.get('collected_count', '?')} | "
                f"评论: {note_info.get('comment_count', '?')}")

            # ===== 阶段4: 滚动评论区 =====
            # 等待评论区出现
            try:
                page.wait_for_selector(".comment-item, [class*='comment-item']", timeout=15000)
            except PwTimeout:
                log("⚠️ 等待评论容器超时", level="warning")

            page.wait_for_timeout(2000)

            log(f"📜 开始滚动加载评论 (上限 {max_comments} 条)...")

            last_count = 0
            no_change = 0

            for rnd in range(SCROLL_ROUNDS):
                page.wait_for_timeout(600)

                # 步骤1: 展开所有折叠内容（回复折叠 + 长评论截断折叠）
                # 类型A：展开回复/子回复（动态数字如"展开 6 条回复"）
                try:
                    expand_selectors = [
                        "text=展开更多回复",
                        "text=展开回复",
                        "text=展开全部回复",
                        "text=查看全部回复",
                        "text=查看全部xx条回复",
                        "text=/展开\\s*\\d+\\s*条回复/",
                    ]
                    for sel in expand_selectors:
                        try:
                            btns = page.locator(sel).all()
                            for btn in btns[:5]:
                                if btn.is_visible(timeout=200):
                                    btn.click(timeout=500, force=True)
                        except Exception as e:
                            log(f"展开回复点击失败: {e}", level="warning")
                except Exception as e:
                    log(f"展开回复流程失败: {e}", level="warning")
                page.wait_for_timeout(400)

                # 类型A（JS兜底）：通过 .show-more 类名 + 文本正则
                try:
                    page.evaluate("""
                        () => {
                            document.querySelectorAll('.show-more').forEach(el => {
                                const text = el.innerText.trim();
                                if (/^展开\s*\d+\s*条回复/.test(text)) {
                                    el.click();
                                }
                            });
                        }
                    """)
                except Exception as e:
                    log(f"JS展开回复失败: {e}", level="warning")
                page.wait_for_timeout(400)

                # 类型B：展开长评论被截断的"展开更多"（单条评论全文）
                try:
                    expand_more = page.locator("text=展开更多")
                    if expand_more.count() > 0:
                        btns = expand_more.all()
                        for btn in btns[:10]:
                            if btn.is_visible(timeout=200):
                                btn.click(timeout=500, force=True)
                except Exception as e:
                    log(f"展开更多点击失败: {e}", level="warning")
                page.wait_for_timeout(400)
                try:
                    full_text = page.locator("text=全文")
                    if full_text.count() > 0:
                        btns = full_text.all()
                        for btn in btns[:5]:
                            if btn.is_visible(timeout=200):
                                btn.click(timeout=500, force=True)
                except Exception as e:
                    log(f"展开全文点击失败: {e}", level="warning")
                page.wait_for_timeout(400)

                # 步骤2: 在 .note-scroller 内滚动到底部（唯一滚动，无全屏副作用）
                try:
                    scroller = page.locator('.note-scroller').first
                    if scroller.count() > 0:
                        scroller.evaluate("el => el.scrollTop = el.scrollHeight")
                except Exception as e:
                    log(f"滚动评论失败: {e}", level="warning")
                page.wait_for_timeout(SCROLL_WAIT_MS)

                # 点击"加载更多"按钮
                for sel in [
                    "text=加载更多", "text=查看更多评论", "text=查看更多",
                ]:
                    try:
                        btns = page.locator(sel).all()
                        for btn in btns[:2]:
                            try:
                                if btn.is_visible(timeout=300):
                                    btn.click(timeout=1000, force=True)
                                    page.wait_for_timeout(600)
                            except Exception as e:
                                log(f"加载更多点击失败: {e}", level="warning")
                    except Exception as e:
                        log(f"加载更多流程失败: {e}", level="warning")

                # 提取当前评论
                comments = page.evaluate(EXTRACT_COMMENTS_JS)
                new_count = 0
                for c in comments:
                    key = (c.get("username", "") + "|" + c.get("content", "")[:40]).strip()
                    if key and key not in seen_keys and c.get("content"):
                        seen_keys.add(key)
                        all_comments.append(c)
                        new_count += 1

                cur = len(all_comments)

                if cur == last_count:
                    no_change += 1
                    if no_change >= NO_CHANGE_THRESHOLD:
                        log(f"   ✓ 连续{NO_CHANGE_THRESHOLD}轮无新评论，停止滚动")
                        break
                else:
                    no_change = 0
                    if new_count > 0:
                        log(f"   📊 当前 {cur} 条 (本轮新增 {new_count})")
                    elif rnd % 5 == 0:
                        log(f"   ... 当前 {cur} 条评论")

                last_count = cur
                if cur >= max_comments:
                    log(f"   ✓ 已达上限 {max_comments} 条")
                    break

            log(f"   ✅ 滚动结束，共 {len(all_comments)} 条评论")

        except Exception as e:
            log(f"❌ 爬取过程出错: {e}", level="error")
            import traceback
            traceback.print_exc()
        finally:
            context.close()
            log("🔒 浏览器已关闭")

    return note_info, all_comments


# ========== Excel 导出 ==========

def save_to_excel(note_info: dict, comments: List[Dict], filepath: str, note_url: str = ""):
    log(f"📊 正在生成Excel: {filepath}")

    wb = Workbook()

    header_font = Font(name="Microsoft YaHei", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="FFFF2442", end_color="FFFF2442", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    data_font = Font(name="Microsoft YaHei", size=10)
    data_align = Alignment(vertical="top", wrap_text=True)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side("thin", "FFD0D0D0"), right=Side("thin", "FFD0D0D0"),
        top=Side("thin", "FFD0D0D0"), bottom=Side("thin", "FFD0D0D0"),
    )

    # ===== 合并为单个 Sheet: 每条评论一行，包含帖子信息字段 =====
    ws = wb.active
    ws.title = "完整数据"

    headers = [
        "帖子标题", "作者", "作者ID", "帖子ID", "发布时间",
        "点赞数", "收藏数", "评论数(官方)", "分享数",
        "标签", "帖子正文",
        "序号", "评论类型", "评论ID", "用户名", "用户ID",
        "用户标签", "评论内容", "评论日期", "位置/IP", "评论点赞数",
        "抓取时间", "笔记网址",
    ]
    widths = [30, 16, 30, 20, 14, 10, 10, 12, 10, 30, 60,
              6, 8, 32, 16, 30, 16, 70, 12, 10, 8, 18, 50]

    for col, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font, cell.fill, cell.alignment, cell.border = header_font, header_fill, header_align, thin_border
        ws.column_dimensions[chr(64 + col) if col <= 26 else "AA"].width = w

    post_base = {
        "title": note_info.get("title", ""),
        "author": note_info.get("author", ""),
        "author_id": note_info.get("author_id", ""),
        "note_id": note_info.get("note_id", ""),
        "publish_time": note_info.get("publish_time", ""),
        "liked_count": note_info.get("liked_count", ""),
        "collected_count": note_info.get("collected_count", ""),
        "comment_count": note_info.get("comment_count", ""),
        "share_count": note_info.get("share_count", ""),
        "tags": ", ".join(note_info.get("tags", [])),
        "content": note_info.get("content", ""),
        "note_url": note_url,
    }

    for i, c in enumerate(comments, 1):
        row_data = [
            post_base["title"],
            post_base["author"],
            post_base["author_id"],
            post_base["note_id"],
            post_base["publish_time"],
            post_base["liked_count"],
            post_base["collected_count"],
            post_base["comment_count"],
            post_base["share_count"],
            post_base["tags"],
            post_base["content"],
            i,
            "回复" if c.get("is_sub") else "主评论",
            c.get("comment_id", ""),
            c.get("username", ""),
            c.get("user_id", ""),
            c.get("user_tags", ""),
            c.get("content", ""),
            c.get("date", ""),
            c.get("location", ""),
            c.get("likes", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            post_base["note_url"],
        ]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=i + 1, column=col, value=val)
            cell.font, cell.border = data_font, thin_border
            cell.alignment = center_align if col in (6, 7, 8, 9, 12, 13, 19, 20, 21, 22, 23) else data_align

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:W{len(comments) + 1}"

    wb.save(filepath)
    log(f"   ✅ Excel已保存: {filepath}")
    return filepath


# ========== 主程序 ==========

def main():
    args = parse_args()

    # login-only 模式：只登录不爬取
    if args.login_only:
        print("\n  🔑 登录模式：仅打开浏览器登录小红书\n")
        scrape_with_playwright(
            args.url, max_comments=0, headless=False, login_only=True,
        )
        return

    if args.urls_file:
        with open(args.urls_file, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        print(f"\n{'='*70}")
        print(f"  小红书批量爬取模式 — 共 {len(urls)} 个链接")
        print(f"  最大评论数: {args.max_comments}")
        print(f"{'='*70}\n")
        for i, url in enumerate(urls, 1):
            print(f"\n{'─'*70}")
            print(f"  [{i}/{len(urls)}] 正在爬取: {url}")
            print(f"{'─'*70}\n")
            args.url = url
            _run_single(args)
        print(f"\n{'='*70}")
        print(f"  ✅ 全部完成！共爬取 {len(urls)} 个链接")
        print(f"{'='*70}\n")
        return

    _run_single(args)


def _run_single(args):

    print(f"\n{'='*70}")
    print(f"  小红书笔记爬虫 v2 — 先登录再爬取")
    print(f"{'='*70}")

    note_info = {}
    comments = []

    if args.local_file:
        print(f"  模式: 本地HTML解析")
        print(f"  文件: {args.local_file}")
        print(f"{'='*70}\n")
        try:
            note_info, comments = parse_local_html(args.local_file)
        except Exception as e:
            log(f"❌ 解析失败: {e}", level="error")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print(f"  模式: 在线爬取（先登录）")
        print(f"  URL: {args.url}")
        print(f"  最大评论数: {args.max_comments}")
        print(f"{'='*70}\n")

        for attempt in range(1, RETRY_TIMES + 1):
            try:
                note_info, comments = scrape_with_playwright(
                    args.url,
                    max_comments=args.max_comments,
                    clear_profile=args.clear_profile,
                    headless=args.headless,
                )
                if comments:
                    break
                if attempt < RETRY_TIMES:
                    log(f"⚠️ 第{attempt}次尝试未获取评论，{attempt * 3}秒后重试...", level="warning")
                    time.sleep(attempt * 3)
            except Exception as e:
                log(f"❌ 第{attempt}次尝试失败: {e}", level="error")
                if attempt < RETRY_TIMES:
                    time.sleep(attempt * 3)
                else:
                    raise

    # 最终去重
    seen = set()
    unique_comments = []
    for c in comments:
        key = (c.get("username", "") + "|" + c.get("content", "")[:40]).strip()
        if key and key not in seen and c.get("content"):
            seen.add(key)
            unique_comments.append(c)

    log(f"📦 最终有效评论数: {len(unique_comments)}")

    if not note_info and not unique_comments:
        log("⚠️ 未获取到任何数据", level="warning")
        print(f"\n{'='*70}")
        print(f"  ⚠️ 未获取到数据")
        print(f"{'='*70}\n")
        sys.exit(1)

    # 保存Excel
    if args.output_file:
        output_path = args.output_file
    else:
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', note_info.get("title", "xhs"))[:20]
        output_path = os.path.join(OUTPUT_DIR, f"xhs_{safe_title}_{ts}.xlsx")

    save_to_excel(note_info, unique_comments, output_path, note_url=args.url)

    # 统计
    main_comments = sum(1 for c in unique_comments if not c.get("is_sub"))
    sub_comments = sum(1 for c in unique_comments if c.get("is_sub"))

    print(f"\n{'='*70}")
    print(f"  ✅ 爬取完成")
    print(f"  帖子: {note_info.get('title', 'N/A')[:40]}")
    print(f"  主评论: {main_comments} 条")
    print(f"  回复: {sub_comments} 条")
    print(f"  评论总计: {len(unique_comments)} 条")
    print(f"\n  📊 输出文件: {output_path}")
    print(f"{'='*70}\n")

    return output_path


if __name__ == "__main__":
    main()
