#!/usr/bin/env python3
"""
京东商品评论爬虫 - 核心模块
与天猫爬虫架构一致: Playwright持久化浏览器 + page.evaluate() JS注入提取
用法:
  python3 run.py 100249710729               # 单商品(ID)
  python3 run.py --shop <店铺URL>            # 整店采集
  python3 run.py --max 200 100249710729     # 限制条数
  python3 run.py --batch <链接文件或逗号分隔>  # 批量模式
"""
import os, re, sys, json, time, random, argparse, logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# 接入统一的浏览器配置和登录管理
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.browser import STEALTH_JS, DEFAULT_USER_AGENT, DEFAULT_VIEWPORT, BROWSER_ARGS
from common.login_helper import (
    ensure_session, get_smart_headless, is_session_valid,
    mark_session_valid, get_profile_dir,
)

from playwright.sync_api import sync_playwright, TimeoutError as PT
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = str(get_profile_dir("jd"))  # 统一 profile 目录
OUTPUT_DIR = str(BASE_DIR / "output")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

JD_ITEM_URL = "https://item.jd.com/{product_id}.html"
PLATFORM = "jd"

# ============ 工具函数 ============
def extract_product_id(url_or_id):
    """从链接或纯数字中提取京东商品ID"""
    s = str(url_or_id).strip()
    if re.match(r'^\d+$', s): return s
    m = re.search(r'item\.jd\.com/(\d+)', s)
    if m: return m.group(1)
    m = re.search(r'/(\d{8,})\.html', s)
    return m.group(1) if m else None

def rd(min_s=0.5, max_s=2.0):
    time.sleep(random.uniform(min_s, max_s))

def clean_text(text):
    if not text: return ''
    return re.sub(r'\n{3,}', '\n\n', re.sub(r' {2,}', ' ', text.strip()))

# ============ 浏览器管理 ============
def create_context(p, headless=False):
    """创建浏览器上下文（使用统一的反检测配置）"""
    return p.chromium.launch_persistent_context(
        PROFILE_DIR, headless=headless,
        args=BROWSER_ARGS,  # 使用统一的反检测参数
        viewport=DEFAULT_VIEWPORT,
        user_agent=DEFAULT_USER_AGENT,
        locale="zh-CN",
        bypass_csp=True,
    )

def check_login(page):
    """检查登录状态（使用统一 session 管理）"""
    from common.login_helper import check_and_login_if_needed
    return check_and_login_if_needed(page, PLATFORM)

# ============ 页面导航 ============
def go_product(page, pid):
    url = JD_ITEM_URL.format(product_id=pid)
    print(f"📄 {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    rd(2, 3)
    check_login(page)

    # 等待React SPA渲染完成 — 京东是CSR，需要等JS bundle执行
    # 等待页面中关键元素出现（商品名、价格等），最多等20秒
    print("  ⏳ 等待页面渲染...")
    try:
        page.wait_for_selector(
            '.sku-name, .itemInfo-wrap, [class*="product"], .p-price, .summary-price',
            timeout=20_000
        )
        print("  ✅ 页面已渲染")
    except Exception as e:
        logger.warning(f"渲染超时(20s): {e}")
    rd(2, 3)


def get_product_info(page):
    """提取商品名称和价格 — 优先用京东专用选择器，排除扩展插件干扰"""
    info = page.evaluate("""
        () => {
            let name='', price='';

            // 京东商品名专用选择器（排除扩展插件的h1）
            for (let sel of [
                '.sku-name',           // 京东商品主标题
                '.itemInfo-wrap .name', // 旧版京东
                '[class*="itemName"]',  // CSSModule
                '[class*="productName"]',
            ]) {
                let el = document.querySelector(sel);
                if (el && el.textContent.trim().length > 3) {
                    name = el.textContent.trim().slice(0, 80);
                    break;
                }
            }

            // 价格选择器
            for (let sel of [
                '.summary-price .price',
                '.p-price .price',
                '[class*="summaryPrice"]',
                '[class*="jd-price"]',
            ]) {
                let el = document.querySelector(sel);
                if (el) {
                    price = el.textContent.replace(/[^0-9.]/g, '');
                    if (price) break;
                }
            }

            return {name, price};
        }
    """)

    # 兜底：从页面title提取商品名
    if not info.get('name') or info['name'] == '最小单价计算器':
        title = page.title()
        # 京东title格式: "商品名【行情 报价 价格 评测】-京东"
        name_from_title = title.replace('【行情 报价 价格 评测】-京东', '').strip()
        if name_from_title and len(name_from_title) > 3:
            info['name'] = name_from_title
            print(f"  📌 从title提取商品名: {name_from_title[:60]}")

    return info

# ============ 评论提取（核心）============
def open_comment_overlay(page):
    """
    京东新版评论区是浮窗(overlay): 点击「全部评价」→ 弹出 jdc-page-overlay
    关键: 京东是CSR(客户端渲染)，React组件需要时间渲染，选择器必须精确
    """
    # 检查是否已打开
    if page.evaluate("() => !!document.querySelector('[class*=\"_rateListBox\"], .jdc-page-overlay')"):
        print("  ✅ 评论浮窗已打开")
        ensure_all_tab(page)
        return True

    # Step1: 滚动到评论区区域（让「全部评价」按钮进入视口）
    page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.55)")
    rd(2, 3)

    # Step2: 精确定位「全部评价」按钮
    # text-is 只匹配直接文本内容为"全部评价"的元素（而非子元素包含）
    # has-text 会匹配子元素中包含该文本的元素，太宽泛
    click_targets = [
        'div:text-is("全部评价")',       # 最精确：div的直接文本是"全部评价"
        'span:text-is("全部评价")',
        'a:text-is("全部评价")',
        # 退而求其次
        'div:has-text("全部评价")',
        'text=全部评价',
    ]

    clicked = False
    for sel in click_targets:
        try:
            els = page.locator(sel).all()
            for el in els:
                if el.is_visible():
                    # 检查元素确实在页面主体内（排除扩展注入的DOM）
                    in_body = el.evaluate(
                        "el => !el.closest('#immersive-translate-popup, #fk-search-root, #fitkun-drop-panel, .calculator-container')"
                    )
                    if in_body:
                        el.scroll_into_view_if_needed()
                        rd(0.5, 1)
                        el.click()
                        print(f"  ✅ 点击「全部评价」: {sel}")
                        clicked = True
                        break
            if clicked:
                break
        except Exception as e:
            logger.debug(f"点击失败: {e}")
            continue

    if not clicked:
        print("  ⚠️ 未找到可点击的「全部评价」按钮")
        return False

    # Step3: 等待浮窗打开（React渲染需要时间）
    print("  ⏳ 等待浮窗渲染...")
    try:
        page.wait_for_selector(
            '[class*="_rateListBox"], .jdc-page-overlay',
            timeout=12_000
        )
        print("  ✅ 评论浮窗已弹出")
        rd(2, 3)
        ensure_all_tab(page)
        return True
    except Exception as e:
        logger.warning(f"浮窗未在12秒内弹出: {e}")
        has_verify = page.evaluate(
            "() => !!document.querySelector('[class*=\"verify\"], [class*=\"captcha\"], [class*=\"spider\"]')"
        )
        if has_verify:
            print("  ⚠️ 检测到验证码/风控，需手动处理")
        return False


def ensure_all_tab(page):
    """确保在「全部」标签页（而非仅好评/图视频/追评等）"""
    switch_to_tab(page, '全部')


def switch_to_tab(page, tab_name):
    """切换到指定评论分类标签（全部/好评/中评/差评/图视频）"""
    try:
        # 找已激活的标签
        active_tag = page.evaluate("""
            () => {
                let tag = document.querySelector('._tag-active_rgt47_31 [class*="tag-name"]');
                return tag ? tag.textContent.trim() : '';
            }
        """)
        if active_tag == tab_name:
            print(f"  🏷️ 已在「{tab_name}」标签")
            return True

        # 点击目标标签
        tag_selectors = [
            f'span:text-is("{tab_name}")',
            f'div:text-is("{tab_name}")',
            f'[class*="tag-name"]:text-is("{tab_name}")',
            f'span:has-text("{tab_name}")',
        ]
        for sel in tag_selectors:
            try:
                tags = page.locator(sel).all()
                for t in tags:
                    if t.is_visible():
                        t.click()
                        print(f"  ✅ 切换到「{tab_name}」标签")
                        rd(2, 3)
                        # 等待新内容加载
                        try:
                            page.wait_for_load_state("networkidle", timeout=8_000)
                        except Exception as e:
                            logger.debug(f"等待加载失败: {e}")
                            pass
                        return True
            except Exception as e:
                logger.debug(f"标签选择失败: {e}")
                continue
        print(f"  ⚠️ 未找到「{tab_name}」标签")
        return False
    except Exception as e:
        logger.warning(f"切换标签失败: {e}")
        return False

def extract_reviews_js(page):
    """
    page.evaluate注入JS提取评论
    基于京东实际DOM结构 — 浮窗内的jdc-pc-rate-card卡片
    """
    return page.evaluate("""
        () => {
            const results=[], seen=new Set();

            // === 定位评论卡片 ===
            let cards = [];

            // 1. 优先：浮窗内的 _listItem
            let overlay = document.querySelector('[class*="_rateListBox"], .jdc-page-overlay');
            if (overlay) {
                cards = overlay.querySelectorAll('[class*="_listItem"]');
            }

            // 2. 兜底：直接找 jdc-pc-rate-card
            if (!cards.length) {
                cards = document.querySelectorAll('.jdc-pc-rate-card');
            }

            // 3. 再兜底
            if (!cards.length) {
                for (let sel of [
                    '.comment-item', '[class*="comment-item"]',
                    '[class*="CommentItem"]', '[class*="evaluation"]'
                ]) {
                    let nodes = document.querySelectorAll(sel);
                    if (nodes.length >= 2) { cards = Array.from(nodes); break; }
                }
            }

            for (let el of cards) {
                try {
                    let ft = el.textContent || '';
                    if (ft.length < 10) continue;

                    // === 昵称: .jdc-pc-rate-card-nick ===
                    let nick = '';
                    let nickEl = el.querySelector('.jdc-pc-rate-card-nick');
                    if (nickEl) nick = nickEl.textContent.trim().slice(0, 20);

                    // === 评分: .jdc-pc-icon-star-good ===
                    let score = 5;
                    if (el.querySelector('.jdc-pc-icon-star-good')) score = 5;

                    // === 内容: .jdc-pc-rate-card-main-desc ===
                    let content = '';
                    let descEl = el.querySelector('.jdc-pc-rate-card-main-desc');
                    if (descEl) content = descEl.textContent.trim();

                    // 兜底：找 span 的最长文本
                    if (!content || content.length < 3) {
                        let spans = el.querySelectorAll('.jdc-pc-rate-card-main span, [class*="desc"], [class*="content"]');
                        let longest = '';
                        for (let s of spans) {
                            let t = s.textContent.trim();
                            if (t.length > longest.length && t.length < 3000 && !t.includes('star-good')) {
                                longest = t;
                            }
                        }
                        if (longest.length > 3) content = longest;
                    }

                    // 最后兜底
                    if (!content || content.length < 3) {
                        content = ft.replace(/商家回复[\\s\\S]*$/g, '').replace(/回复\\d*|有用\\d*/g, '').trim();
                        // 取最可能的段落
                        let lines = content.split(/[\\n]+/).filter(l => l.length > 10);
                        content = lines.length > 0 ? lines.join(' ') : content;
                    }

                    // === 日期: .date.list ===
                    let date = '';
                    let year = new Date().getFullYear();  // 当前年份
                    let dateEl = el.querySelector('.date.list, .date, [class*="time"]');
                    if (dateEl) {
                        date = dateEl.textContent.trim().replace(/[年月]/g, '-').replace(/日/g, '');
                        // 补全年份：纯MM-DD格式 → YYYY-MM-DD
                        if (/^\\d{1,2}[-\\/]\\d{1,2}$/.test(date)) {
                            date = year + '-' + date.replace('/', '-');
                        }
                    }
                    if (!date) {
                        let dm = ft.match(/(\\d{4}[-.\\/]\\d{1,2}[-.\\/]\\d{1,2})/);
                        if (dm) {
                            date = dm[1].replace(/[./]/g, '-');
                        } else {
                            // 纯MM-DD兜底
                            let sm = ft.match(/(?<![\\d])(\\d{1,2}[-.\\/]\\d{1,2})(?![\\d])/);
                            if (sm) date = year + '-' + sm[1].replace('.', '-').replace('/', '-');
                        }
                    }

                    // === SKU: .info (在 rate-card-info top 里) ===
                    let sku = '';
                    let infoEl = el.querySelector('.info');
                    if (infoEl) sku = infoEl.textContent.trim().slice(0, 40);

                    // === 图片数 ===
                    let imgCount = el.querySelectorAll(
                        '.jdc-pc-rate-card-images img, .jdc-image img, [class*="media-list"] img'
                    ).length;

                    // === 追评 ===
                    let follow = '';
                    let fe = el.querySelector('[class*="after"], [class*="append"], [class*="follow"]');
                    if (fe) { let t = fe.textContent.trim(); if (t.length > 10 && !t.includes('商家回复')) follow = t.slice(0, 200); }

                    // === 去重 ===
                    let key = (nick + content).slice(0, 80);
                    if (seen.has(key) || content.length < 4) continue;
                    seen.add(key);

                    results.push({
                        nick: nick || '匿名用户',
                        content: content.replace(/商家回复[\\s\\S]*$/g, '').trim().slice(0, 500),
                        date, sku, score,
                        img_count: imgCount,
                        follow
                    });
                    if (results.length >= 1000) break;
                } catch (e) {}
            }
            return results;
        }
    """)

# ============ 翻页/滚动处理（浮窗虚拟滚动）============
def scroll_overlay_to_load(page):
    """
    京东评论浮窗使用 virtuoso 虚拟滚动（data-viewport-type="window"）,
    需要通过多种方式触发加载更多：
    1. 在浮窗容器内滚动
    2. window 滚动（virtuoso viewport-type=window 时监听 window 滚动）
    3. 触发 wheel 事件
    """
    return page.evaluate("""
        () => {
            let overlay = document.querySelector('[class*="_rateListBox"], .jdc-page-overlay');
            if (!overlay) return { scrolled: false, reason: 'no overlay' };

            // 找到列表容器
            let listCtn = overlay.querySelector('[class*="_list_"], [class*="rateListContainer"]');
            let target = listCtn || overlay;
            let oldTop = target.scrollTop, oldH = target.scrollHeight;

            // 方式1: 在列表容器内滚动
            if (target.scrollHeight > target.clientHeight) {
                target.scrollTop = target.scrollHeight;
            }

            // 方式2: 虚拟滚动 viewport (virtuoso 的 viewport 容器)
            let viewport = overlay.querySelector('[data-viewport-type="window"]');
            if (viewport && viewport.scrollHeight > viewport.clientHeight) {
                viewport.scrollTop = viewport.scrollHeight;
            }

            // 方式3: 滚动 window (virtuoso viewport-type=window 场景)
            window.scrollBy(0, 800);
            window.dispatchEvent(new Event('scroll', { bubbles: false }));

            // 方式4: 触发 wheel 事件 (模仿用户滚轮操作)
            target.dispatchEvent(new WheelEvent('wheel', {
                deltaY: 1200, deltaMode: 0, bubbles: true, cancelable: true
            }));

            let changed = (target.scrollTop !== oldTop) || (target.scrollHeight !== oldH);
            return { scrolled: changed, oldH, newH: target.scrollHeight };
        }
    """)


def has_verify_challenge(page):
    """检测是否有验证码/风控弹窗"""
    indicators = page.evaluate("""
        () => {
            return !!(
                document.querySelector('[class*="verify"], [class*="captcha"], [class*="spider"]') ||
                document.querySelector('iframe[src*="verify"], iframe[src*="captcha"]') ||
                document.querySelector('.jd-dialog-verify, .verify-code, [class*="sliderVerify"]') ||
                (document.title || '').includes('验证') ||
                window.location.href.includes('verify')
            );
        }
    """)
    return indicators


def paginate_collect(page, max_count=5000):
    """
    浮窗虚拟滚动 + 验证码检测 + 断点续爬
    验证码弹出后页面会刷新、浮窗关闭，需要重新打开浮窗继续
    """
    all_r, stall = [], 0
    verify_count = 0  # 验证码次数

    # 用set做去重（nick+content前80字符）
    seen_keys = set()

    # 打开浮窗
    if not open_comment_overlay(page):
        print("  ❌ 评论浮窗打开失败，无法爬取")
        return []

    rd(3, 4)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception as e:
        logger.debug(f"等待网络空闲失败: {e}")
        pass

    for rnd in range(500):  # 多给一些轮次
        rd(2, 4)  # 加长等待，更像人类

        # === 验证码检测 ===
        if has_verify_challenge(page):
            verify_count += 1
            print(f"\n  ⚠️ 检测到验证码（第{verify_count}次）！请在浏览器中手动完成验证")
            print("  完成验证后程序将自动继续...")
            # 等待验证码消失（页面可能刷新）
            while has_verify_challenge(page):
                rd(3, 5)
            rd(5, 8)
            print("  ✅ 验证已通过，恢复爬取")

            # 页面可能已刷新，浮窗已关闭，需要重新打开
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception as e:
                logger.debug(f"验证后等待失败: {e}")
                pass

            has_overlay = page.evaluate(
                "() => !!document.querySelector('[class*=\"_rateListBox\"], .jdc-page-overlay')"
            )
            if not has_overlay:
                print("  🔄 浮窗已关闭，重新打开...")
                if not open_comment_overlay(page):
                    print("  ❌ 重新打开浮窗失败")
                    break
                rd(3, 4)
            continue

        # === 检测浮窗是否还在 ===
        has_overlay = page.evaluate(
            "() => !!document.querySelector('[class*=\"_rateListBox\"], .jdc-page-overlay')"
        )
        if not has_overlay:
            print("  ⚠️ 浮窗意外关闭，尝试重新打开...")
            if not open_comment_overlay(page):
                # 可能页面整体刷新了，等一等再试
                rd(5, 8)
                try:
                    page.wait_for_load_state("networkidle", timeout=15_000)
                except Exception as e:
                    logger.debug(f"等待重试失败: {e}")
                    pass
                if not open_comment_overlay(page):
                    print("  ❌ 无法重新打开浮窗")
                    break
            rd(3, 4)

        # === 提取当前可见评论（带去重）===
        new_batch = extract_reviews_js(page)
        before = len(all_r)
        for r in new_batch:
            # 双重去重key：昵称+内容前80字符
            key = f"{r.get('nick','')}|{r.get('content','')[:80]}"
            if key not in seen_keys and r.get('content', '').strip():
                seen_keys.add(key)
                all_r.append(r)

        added = len(all_r) - before
        if rnd % 5 == 0 or added > 0:
            vmsg = f" | 验证码{verify_count}次" if verify_count else ""
            print(f"  📊 第{rnd+1}轮: +{added}条, 累计{len(all_r)}条{vmsg}")

        if len(all_r) >= max_count:
            print(f"  ✓ 已达上限 {max_count} 条")
            break

        if added == 0:
            stall += 1
            if stall >= 15:
                print(f"  ⏹️ 连续{stall}轮无新数据，停止")
                break
        else:
            stall = 0

        # 滚动加载
        scroll_overlay_to_load(page)
        rd(1, 2)

        # 加强滚动


        if added == 0:
            try:
                overlay_el = page.locator('[class*="_rateListBox"]').first
                overlay_el.hover()
                page.mouse.wheel(0, 2000)
            except Exception as e:
                logger.debug(f"悬停滚动失败: {e}")
                pass

        rd(2, 3)
        try:
            page.wait_for_load_state("networkidle", timeout=6_000)
        except Exception as e:
            logger.debug(f"等待加载失败: {e}")
            pass

    # 最终去重
    print(f"\n  🔍 本次去重中...")
    final_seen = set()
    final_reviews = []
    for r in all_r:
        key = f"{r.get('nick','')}|{r.get('content','')[:120]}"
        if key not in final_seen:
            final_seen.add(key)
            final_reviews.append(r)
    dupes = len(all_r) - len(final_reviews)
    if dupes:
        print(f"  🧹 去重移除 {dupes} 条重复")

    print(f"  📊 本Tab: {len(final_reviews)} 条 (验证码 {verify_count} 次)")
    return final_reviews


# ============ 多Tab采集（突破虚拟滚动限制）============
def collect_all_tabs(page, max_per_tab=1000):
    """
    京东虚拟滚动在每个Tab下有限制（~300条），
    需要切换「全部→好评→中评→差评→图/视频」覆盖更多评论
    """
    all_reviews = []
    global_keys = set()

    # 打开浮窗
    if not open_comment_overlay(page):
        print("  ❌ 评论浮窗打开失败")
        return []

    rd(3, 4)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception as e:
        logger.debug(f"等待网络空闲失败: {e}")
        pass

    # Tab顺序：全部 → 好评(最多) → 中评 → 差评 → 图/视频
    tabs_to_try = ['全部', '好评', '中评', '差评', '图/视频']

    for tab_name in tabs_to_try:
        if not switch_to_tab(page, tab_name):
            continue

        # 检查此Tab的评论数
        try:
            tab_count_text = page.evaluate(f"""
                () => {{
                    let tags = document.querySelectorAll('._tag_rgt47_12');
                    for (let t of tags) {{
                        let name = t.querySelector('[class*="tag-name"]');
                        let count = t.querySelector('[class*="tag-comment"]');
                        if (name && name.textContent.trim() === '{tab_name}' && count) {{
                            return count.textContent.trim();
                        }}
                    }}
                    return '';
                }}
            """)
            if tab_count_text:
                print(f"  📊 Tab「{tab_name}」约{tab_count_text}条")
        except Exception as e:
            logger.debug(f"获取Tab评论数失败: {e}")
            pass

        # 采集当前Tab（paginate_collect 但是不关闭浮窗、不去重）
        tab_reviews = _scroll_collect_one_tab(page, max_per_tab, tab_name)

        # 跨Tab合并去重
        added = 0
        for r in tab_reviews:
            key = f"{r.get('nick','')}|{r.get('content','')[:120]}"
            if key not in global_keys:
                global_keys.add(key)
                all_reviews.append(r)
                added += 1

        print(f"  ✅ Tab「{tab_name}」: +{added}条新评论，累计{len(all_reviews)}条\n")

    # 关闭浮窗
    close_overlay(page)
    print(f"\n✨ 全部Tab采集完成: {len(all_reviews)} 条评论")
    return all_reviews


def _scroll_collect_one_tab(page, max_count, tab_label):
    """在单个Tab内滚动采集评论（不打开/关闭浮窗）"""
    results, stall = [], 0

    for rnd in range(500):
        rd(1, 2)

        # 验证码检测
        if has_verify_challenge(page):
            print(f"\n  ⚠️ [{tab_label}] 检测到验证码！请在浏览器中手动完成")
            while has_verify_challenge(page):
                rd(3, 5)
            rd(5, 8)
            print(f"  ✅ [{tab_label}] 验证通过，恢复")

            # 检查浮窗还在不在
            if not page.evaluate("() => !!document.querySelector('[class*=\"_rateListBox\"]')"):
                open_comment_overlay(page)
                rd(3, 4)
                switch_to_tab(page, tab_label)
                rd(3, 4)
            continue

        # 检查浮窗
        if not page.evaluate("() => !!document.querySelector('[class*=\"_rateListBox\"]')"):
            print(f"  🔄 [{tab_label}] 浮窗关闭，重新打开...")
            if not open_comment_overlay(page):
                break
            rd(3, 4)
            switch_to_tab(page, tab_label)
            rd(3, 4)

        # 提取
        batch = extract_reviews_js(page)
        before = len(results)
        seen = {(r.get('nick', '') + r.get('content', ''))[:80] for r in results}
        for r in batch:
            k = (r.get('nick', '') + r.get('content', ''))[:80]
            if k not in seen and r.get('content', '').strip():
                seen.add(k)
                results.append(r)

        added = len(results) - before
        if rnd % 10 == 0 or added > 0:
            print(f"  [{tab_label}] 第{rnd+1}轮: +{added}条, 累计{len(results)}条")

        if len(results) >= max_count:
            break

        if added == 0:
            stall += 1
            if stall >= 15:
                break
        else:
            stall = 0

        scroll_overlay_to_load(page)
        rd(1, 2)

        if added == 0:
            try:
                page.locator('[class*="_rateListBox"]').first.hover()
                page.mouse.wheel(0, 2000)
            except Exception as e:
                logger.debug(f"悬停浮窗失败: {e}")
                pass

        rd(2, 3)
        try:
            page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception as e:
            logger.debug(f"等待加载失败: {e}")
            pass

    # 最终去重
    final_seen, final_results = set(), []
    for r in results:
        k = f"{r.get('nick','')}|{r.get('content','')[:120]}"
        if k not in final_seen:
            final_seen.add(k)
            final_results.append(r)
    return final_results


def close_overlay(page):
    """关闭评论浮窗"""
    try:
        close_btn = page.locator('._closeIcon_1ygkr_39, [class*="closeIcon"]').first
        if close_btn.is_visible(timeout=2000):
            close_btn.click()
            rd(1, 2)
    except Exception as e:
        logger.warning(f"关闭浮窗失败: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception as e2:
            logger.warning(f"按ESC键失败: {e2}")

# ============ Excel输出 ============
def save_excel(reviews, pinfo, pid, fpath):
    """保存单商品Excel"""
    wb = Workbook(); ws = wb.active; ws.title = "商品评论"
    headers = ["序号","商品名称","商品ID","买家昵称","评分","评论内容","SKU/口味","评论日期","图片数","追评内容"]
    widths = [6,28,18,15,6,60,15,14,8,40]
    hf = PatternFill("solid", fgColor="2F5496"); hfn = Font(name="微软雅黑",size=11,bold=True,color="FFFFFF")
    cf = Font(name="微软雅黑",size=10); ca = Alignment(wrap_text=True,vertical="top")
    tb = Border(left=Side("thin","D9D9D9"),right=Side("thin","D9D9D9"),top=Side("thin","D9D9D9"),bottom=Side("thin","D9D9D9"))
    for i,(h,w) in enumerate(zip(headers,widths),1):
        c=ws.cell(1,i,h);c.fill=hf;c.font=hfn;c.alignment=Alignment(horizontal="center",vertical="center");c.border=tb
        ws.column_dimensions[get_column_letter(i)].width=w
    for ri,r in enumerate(reviews,1):
        for ci,val in enumerate([ri,pinfo.get('name',''),pid,r.get('nick','')[:20],r.get('score',0),r.get('content','')[:500],r.get('sku',''),r.get('date',''),r.get('img_count',0),r.get('follow','')],1):
            c=ws.cell(ri+1,ci,val);c.font=cf;c.alignment=ca;c.border=tb
    ws.freeze_panes="A2";ws.auto_filter.ref=f"A1:{get_column_letter(10)}{len(reviews)+1}"
    wb.save(fpath)
    print(f"  💾 已保存: {fpath}")

def save_merged(all_data, fpath):
    """保存合并总表"""
    wb=Workbook();ws=wb.active;ws.title="评论合集"
    headers=["序号","来源商品","商品ID","买家昵称","评分","评论内容","SKU/口味","评论日期","图片数","追评内容"]
    widths=[6,28,18,15,6,55,15,14,8,35]
    hf=PatternFill("solid",fgColor="2F5496");hfn=Font(name="微软雅黑",size=11,bold=True,color="FFFFFF")
    cf=Font(name="微软雅黑",size=10);ca=Alignment(wrap_text=True,vertical="top")
    tb=Border(left=Side("thin","D9D9D9"),right=Side("thin","D9D9D9"),top=Side("thin","D9D9D9"),bottom=Side("thin","D9D9D9"))
    for i,(h,w) in enumerate(zip(headers,widths),1):
        c=ws.cell(1,i,h);c.fill=hf;c.font=hfn;c.alignment=Alignment(horizontal="center",vertical="center");c.border=tb
        ws.column_dimensions[get_column_letter(i)].width=w
    ri=1
    for pname,reviews in all_data.items():
        for r in reviews:
            for ci,val in enumerate([ri,pname[:30],r.get('product_id',''),r.get('nick','')[:20],r.get('score',0),r.get('content','')[:500],r.get('sku',''),r.get('date',''),r.get('img_count',0),r.get('follow','')],1):
                c=ws.cell(ri+1,ci,val);c.font=cf;c.alignment=ca;c.border=tb
            ri+=1
    ws.freeze_panes="A2";ws.auto_filter.ref=f"A1:{get_column_letter(10)}{ri}"
    wb.save(fpath)
    print(f"📦 合并总表: {fpath} ({ri-1}条)")

# ============ 店铺商品采集 ============
def collect_shop_products(page, shop_url):
    print(f"🏪 {shop_url}")
    page.goto(shop_url, wait_until="domcontentloaded", timeout=30_000)
    rd(3,4); check_login(page)
    for _ in range(5):
        page.evaluate("window.scrollTo(0,document.body.scrollHeight)"); rd(1,2)
    try: page.wait_for_load_state("networkidle", timeout=10_000)
    except Exception as e: logger.warning(f"等待加载状态失败: {e}")
    products = page.evaluate("""
        ()=>{const s=new Set();document.querySelectorAll('a[href*="item.jd.com/"]').forEach(a=>{
            let m=a.href.match(/item\\.jd\\.com\\/(\\d+)/);
            if(m)s.add(JSON.stringify({id:m[1],url:'https://item.jd.com/'+m[1]+'.html',name:a.textContent.trim().slice(0,40)||'商品'+m[1]}))
        });return Array.from(s).map(JSON.parse)}
    """)
    seen=set();uniq=[]
    for p in products:
        if p['id'] not in seen: seen.add(p['id']); uniq.append(p)
    print(f"  📋 发现{len(uniq)}个商品")
    return uniq

# ============ 单商品爬取 ============
def scrape_single(page, url_or_id, max_count=150, output_dir=OUTPUT_DIR):
    pid = extract_product_id(url_or_id)
    if not pid: return None, None
    print(f"\n{'='*40}\n🛒 商品 {pid}\n{'='*40}")
    go_product(page, pid); rd(2,3)
    pinfo = get_product_info(page)
    print(f"  📌 {pinfo.get('name','未知')}")
    reviews = collect_all_tabs(page, max_count)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fpath = os.path.join(output_dir, f"reviews_{pid}_{ts}.xlsx")
    save_excel(reviews, pinfo, pid, fpath)
    return reviews, pinfo

# ============ 批量爬取 ============
def scrape_batch(page, product_list, max_per=100, output_dir=OUTPUT_DIR):
    all_data = {}
    for idx, p in enumerate(product_list, 1):
        print(f"\n{'#'*45}\n# [{idx}/{len(product_list)}]\n{'#'*45}")
        try:
            pid = extract_product_id(p)
            if not pid: continue
            reviews, pinfo = scrape_single(page, pid, max_per, output_dir=output_dir)
            if reviews:
                name = pinfo.get('name', pid)
                for r in reviews: r['product_name'] = name; r['product_id'] = pid
                all_data[name] = reviews
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断，保存已有数据..."); break
        except Exception as e:
            print(f"  ❌ 出错: {e}"); continue
    if all_data:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_merged(all_data, os.path.join(output_dir, f"reviews_京东合集_{ts}.xlsx"))
    return all_data

# ============ 主入口 ============
def main():
    parser = argparse.ArgumentParser(description="京东商品评论爬虫")
    parser.add_argument("target", nargs="?", help="商品ID或链接")
    parser.add_argument("--shop", help="店铺首页URL，采集全店商品")
    parser.add_argument("--batch", help="批量模式（逗号分隔链接或txt文件路径）")
    parser.add_argument("--max", type=int, default=150, help="每个商品最多评论数(默认150)")
    parser.add_argument("--list-products", help="仅列出店铺商品")
    parser.add_argument("--headless", action="store_true", default=False, help="无头模式运行浏览器")
    parser.add_argument("--login-only", action="store_true", default=False, help="仅打开浏览器登录京东")
    parser.add_argument("--output", default=OUTPUT_DIR, help="输出目录")
    args = parser.parse_args()

    # login-only 模式
    if args.login_only:
        print("\n  🔑 登录模式：仅打开浏览器登录京东\n")
        with sync_playwright() as p:
            ctx = create_context(p, headless=False)
            page = ctx.new_page()
            page.add_init_script(STEALTH_JS)
            try:
                ensure_session(page, PLATFORM)
                print("  ✅ 登录完成，session 已缓存")
            finally:
                ctx.close()
        return

    # 智能决定是否 headless
    headless = get_smart_headless(PLATFORM, args.headless)

    output_dir = args.output
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = create_context(p, headless=headless)
        page = ctx.new_page()
        page.add_init_script(STEALTH_JS)  # 注入反检测 JS

        # 仅列出商品
        if args.list_products:
            prods = collect_shop_products(page, args.list_products)
            print("\n商品列表：")
            for pp in prods:
                print(f"  {pp['id']} - {pp['name']}")
            ctx.close(); return

        # 店铺模式
        if args.shop:
            prods = collect_shop_products(page, args.shop)
            scrape_batch(page, [p['url'] for p in prods], args.max, output_dir=output_dir)
            ctx.close(); return

        # 批量模式
        if args.batch:
            if os.path.isfile(args.batch):
                with open(args.batch) as f:
                    items = [l.strip() for l in f if l.strip()]
            else:
                items = [x.strip() for x in args.batch.split(',') if x.strip()]
            scrape_batch(page, items, args.max, output_dir=output_dir)
            ctx.close(); return

        # 单商品模式
        if args.target:
            scrape_single(page, args.target, args.max, output_dir=output_dir)
        else:
            parser.print_help()

        ctx.close()

if __name__ == "__main__":
    main()
