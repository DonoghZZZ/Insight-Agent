#!/usr/bin/env python3
"""
抖音视频信息提取器（独立脚本）
只提取视频基本信息：作者、粉丝、获赞、描述、点赞、转发、发布时间
不爬取评论。用于 CrawlerManager 的信息预览功能。

用法:
  python3 fetch_video_info.py <抖音视频URL>
  python3 fetch_video_info.py --json <抖音视频URL>   # JSON 输出
"""
import sys
import os
import json
import time
import re
import logging

logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))
from common.browser import STEALTH_JS, DEFAULT_USER_AGENT, DEFAULT_VIEWPORT, BROWSER_ARGS

# ══════════════════════════════════════════
# 浏览器端 JS：提取视频信息（复用 douyin_scraper 的代码）
# ══════════════════════════════════════════

EXTRACT_VIDEO_INFO_JS = """
() => {
  const result = {};
  const numRe = /([\\d.]+[万wW]?)/;

  // 1. 视频描述
  const h1 = document.querySelector('h1');
  if (h1 && h1.innerText.trim()) {
    result.desc = h1.innerText.trim();
  }

  // 2. 作者信息
  const userInfoEl = document.querySelector('[data-e2e="user-info"]');
  if (userInfoEl) {
    const text = userInfoEl.innerText || '';
    const fanMatch = text.match(/粉丝\\s*([\\d.]+[万wW]?)/);
    const likeMatch = text.match(/获赞\\s*([\\d.]+[万wW]?)/);
    if (fanMatch) result.followers = fanMatch[1];
    if (likeMatch) result.totalLikes = likeMatch[1];
    const links = userInfoEl.querySelectorAll('a[href*="/user/"]');
    for (const link of links) {
      let t = link.innerText.trim().split('\\n')[0]
        .replace(/\\s*作者$/, '').replace(/认证徽章.*/, '')
        .replace(/优质视频创.*/, '').replace(/视频创.*/, '').trim();
      if (t && t.length > 0 && t.length < 30 &&
          !t.includes('粉丝') && !t.includes('获赞') && t !== '作者') {
        result.author = t; break;
      }
    }
  }

  // 兜底：用头像img的alt
  if (!result.author) {
    const avatarImgs = document.querySelectorAll('img[alt*="头像"]');
    for (const img of avatarImgs) {
      if (img.closest('[data-e2e="comment-list"]')) continue;
      const alt = img.alt;
      const name = alt.replace(/的头像$/, '').replace(/头像$/, '').trim();
      if (name && name.length > 0 && name.length < 30) {
        result.author = name; break;
      }
    }
  }

  // 3. 点赞/评论/收藏/转发
  const e2eMap = {
    'video-player-digg': 'likes',
    'video-player-comment': 'commentCount',
    'video-player-fav': 'favs',
    'video-player-share': 'shares'
  };
  for (const [e2e, key] of Object.entries(e2eMap)) {
    const el = document.querySelector(`[data-e2e="${e2e}"]`);
    if (el) {
      const text = el.innerText.trim();
      const m = text.match(numRe);
      if (m) result[key] = m[1];
    }
  }

  // 如果data-e2e没找到，用操作栏提取
  if (!result.likes) {
    const container = document.querySelector('[data-e2e="feed-comment-icon"]')?.parentElement?.parentElement;
    if (container) {
      const nums = [];
      for (const el of container.querySelectorAll(':scope > div')) {
        const text = el.innerText?.trim() || '';
        const m = text.match(numRe);
        if (m) nums.push(m[1]);
      }
      if (nums.length >= 1) result.likes = nums[0];
      if (nums.length >= 2) result.commentCount = nums[1];
      if (nums.length >= 3) result.favs = nums[2];
      if (nums.length >= 4) result.shares = nums[3];
    }
  }

  // 4. 发布时间
  const publishEl = document.querySelector('[data-e2e="detail-video-publish-time"]');
  if (publishEl) {
    result.publishTime = (publishEl.innerText || '').replace(/^发布时间[：:]\\s*/, '').trim();
  }

  return result;
}
"""

# ══════════════════════════════════════════
# 反检测 JS（复用 douyin_scraper）
# ══════════════════════════════════════════

ANTI_DETECTION_JS = STEALTH_JS


def create_browser_context(p):
    profile_dir = os.path.join(SCRIPT_DIR, "browser_profile_douyin")
    os.makedirs(profile_dir, exist_ok=True)
    context = p.chromium.launch_persistent_context(
        profile_dir,
        headless=False,
        args=BROWSER_ARGS,
        viewport=DEFAULT_VIEWPORT,
        user_agent=DEFAULT_USER_AGENT,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        bypass_csp=True,
    )
    return context


def extract_video_info(url: str) -> dict:
    """打开抖音视频页面，提取基本信息"""
    from playwright.sync_api import sync_playwright

    result = {
        "url": url,
        "author": "",
        "followers": "",
        "totalLikes": "",
        "desc": "",
        "likes": "",
        "shares": "",
        "publishTime": "",
        "error": "",
    }

    try:
        with sync_playwright() as p:
            context = create_browser_context(p)
            page = context.new_page()
            page.add_init_script(ANTI_DETECTION_JS)

            print(f"📂 正在加载页面: {url}", file=sys.stderr)
            page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # 等待页面渲染
            print("⏳ 等待页面渲染…", file=sys.stderr)
            page.wait_for_timeout(5000)

            # 等待 h1 出现（视频描述）
            try:
                page.wait_for_selector("h1", timeout=10000)
            except Exception as e:
                logger.warning(f"等待h1元素失败: {e}")

            # 额外等待确保动态内容加载
            page.wait_for_timeout(2000)

            # 提取信息
            print("🔍 提取视频信息…", file=sys.stderr)
            info = page.evaluate(EXTRACT_VIDEO_INFO_JS)
            if info:
                result.update(info)

            # 页面标题作为后备
            try:
                title = page.title()
                if title and not result.get("desc"):
                    result["desc"] = title
            except Exception as e:
                logger.warning(f"获取页面标题失败: {e}")

            context.close()

    except Exception as e:
        result["error"] = str(e)[:150]

    return result


def main():
    output_json = False
    args = sys.argv[1:]

    if "--json" in args:
        output_json = True
        args.remove("--json")

    if not args:
        print("用法: python3 fetch_video_info.py [--json] <抖音视频URL>", file=sys.stderr)
        sys.exit(1)

    url = args[0]

    print(f"🎬 抖音视频信息提取", file=sys.stderr)
    print(f"   目标: {url}", file=sys.stderr)
    print(f"   模式: 可见浏览器（提取后自动关闭）", file=sys.stderr)
    print(file=sys.stderr)

    result = extract_video_info(url)

    if output_json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("\n" + "=" * 50)
        print("📋 视频信息")
        print("=" * 50)
        print(f"  来源链接: {result['url']}")
        print(f"  视频作者: {result['author'] or '—'}")
        print(f"  粉丝数:   {result['followers'] or '—'}")
        print(f"  获赞数:   {result['totalLikes'] or '—'}")
        print(f"  视频描述: {result['desc'] or '—'}")
        print(f"  点赞数:   {result['likes'] or '—'}")
        print(f"  转发数:   {result['shares'] or '—'}")
        print(f"  发布时间: {result['publishTime'] or '—'}")

        if result.get("error"):
            print(f"\n⚠️  错误: {result['error']}")

    if result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
