#!/usr/bin/env python3
"""
登录会话管理模块

统一管理各平台的登录状态：
1. 首次运行 → 弹出浏览器让用户手动登录 → 缓存 profile
2. 再次运行 → 检测 profile 是否有效 → 有效则 headless 直接爬
3. session 过期 → 重新弹浏览器登录
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.parent  # crawlers/


# ========== Profile 路径管理 ==========

def get_profile_dir(platform: str) -> Path:
    """获取各平台的浏览器 profile 目录"""
    profile_map = {
        "douyin":    SCRIPT_DIR / "douyin" / "browser_profile_douyin",
        "zhihu":     SCRIPT_DIR / "zhihu" / "browser_profile",
        "xiaohongshu": SCRIPT_DIR / "xiaohongshu" / "xhs_browser_profile",
        "tmall":     SCRIPT_DIR / "tmall" / "browser_profile",
        "jd":        SCRIPT_DIR / "jd" / "browser_profile",
    }
    if platform not in profile_map:
        raise ValueError(f"未知平台: {platform}，支持: {list(profile_map.keys())}")
    return profile_map[platform]


# ========== Session 状态文件 ==========

def _state_file(platform: str) -> Path:
    return get_profile_dir(platform) / ".session_state.json"


def _save_state(platform: str, logged_in: bool):
    """保存登录状态"""
    profile = get_profile_dir(platform)
    profile.mkdir(parents=True, exist_ok=True)
    state = {
        "logged_in": logged_in,
        "verified_at": time.time(),
        "verified_date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _state_file(platform).write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load_state(platform: str) -> dict:
    """读取登录状态"""
    sf = _state_file(platform)
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def is_session_valid(platform: str, max_age_hours: float = 24) -> bool:
    """
    判断 session 是否仍然有效（不需要重新登录）
    条件：
      1. profile 目录存在且有内容（至少有 Default 子目录）
      2. session_state.json 存在且 logged_in=true
      3. 距离上次验证不超过 max_age_hours 小时
    """
    profile = get_profile_dir(platform)
    default_dir = profile / "Default"
    if not default_dir.exists():
        return False

    state = _load_state(platform)
    if not state.get("logged_in"):
        return False

    verified_at = state.get("verified_at", 0)
    age_hours = (time.time() - verified_at) / 3600
    if age_hours > max_age_hours:
        return False

    return True


def mark_session_valid(platform: str):
    """标记 session 为有效"""
    _save_state(platform, logged_in=True)


def mark_session_invalid(platform: str):
    """标记 session 为无效（需要重新登录）"""
    _save_state(platform, logged_in=False)


def get_smart_headless(platform: str, requested_headless: bool) -> bool:
    """
    智能决定是否 headless：
      - 用户显式要求 headless → 尊重
      - session 有效 → headless（不需要交互）
      - session 无效/首次 → 非 headless（弹浏览器登录）
    """
    if requested_headless:
        if is_session_valid(platform):
            return True
        else:
            print(f"  ⚠️  {platform} session 无效或已过期，将打开浏览器进行登录")
            return False
    return False


# ========== 登录检测 JS（各平台） ==========

DOUYIN_CHECK_LOGIN_JS = """
() => {
    const checks = {};
    // 1. 检查是否有登录按钮/弹窗（未登录标志）
    const loginBtns = document.querySelectorAll(
        '[class*="login"], [class*="Login"], [data-e2e="login"], .login-guide'
    );
    let hasLoginPrompt = false;
    for (const el of loginBtns) {
        const text = (el.innerText || '').toLowerCase();
        if (text.includes('登录') || text.includes('login') || text.includes('注册')) {
            if (el.offsetParent !== null) { hasLoginPrompt = true; break; }
        }
    }
    checks.has_login_prompt = hasLoginPrompt;

    // 2. 检查是否有用户头像（已登录标志）
    const avatar = document.querySelector(
        '[data-e2e="user-info"] img, .avatar, [class*="avatar"], [class*="Avatar"]'
    );
    checks.has_avatar = !!avatar;

    // 3. 检查 URL 是否在登录页
    checks.url_has_login = window.location.href.includes('/login');

    // 4. 检查 cookie
    checks.has_session_cookie = document.cookie.includes('sessionid') ||
                                 document.cookie.includes('passport_csrf_token') ||
                                 document.cookie.includes('sid_guard');

    // 综合判断
    checks.is_logged_in = !checks.url_has_login &&
                          !checks.has_login_prompt &&
                          (checks.has_avatar || checks.has_session_cookie);
    return checks;
}
"""

ZHIHU_CHECK_LOGIN_JS = """
() => {
    const checks = {};
    checks.url_has_login = window.location.href.includes('/signin') ||
                           window.location.href.includes('/login');
    checks.has_password_input = !!document.querySelector("input[type='password']");
    checks.has_avatar = !!document.querySelector('.AppHeader-profileEntry, .Avatar, [class*="avatar"]');
    checks.has_session_cookie = document.cookie.includes('z_c0');

    checks.is_logged_in = !checks.url_has_login &&
                          !checks.has_password_input &&
                          (checks.has_avatar || checks.has_session_cookie);
    return checks;
}
"""

XHS_CHECK_LOGIN_JS = """
() => {
    const checks = {};
    const loginBtn = document.querySelector('.login-btn, .sign-in, [class*="login-btn"]');
    checks.has_login_btn = !!loginBtn;
    checks.has_session_cookie = document.cookie.includes('web_session') ||
                                 document.cookie.includes('a1');
    checks.url_has_login = window.location.href.includes('/login');
    const userEl = document.querySelector('.user, .avatar-container, .side-bar-user, [class*="user-info"]');
    checks.has_user_element = !!userEl;

    checks.is_logged_in = !checks.url_has_login &&
                          (checks.has_user_element || checks.has_session_cookie);
    return checks;
}
"""

TMALL_CHECK_LOGIN_JS = """
() => {
    const checks = {};
    // 天猫/淘宝统一登录系统
    checks.url_has_login = window.location.href.includes('login.tmall.com') ||
                           window.location.href.includes('login.taobao.com') ||
                           window.location.href.includes('passport.tmall.com');
    // 登录后页面有用户信息
    checks.has_user = !!document.querySelector('.J_UserName, .site-nav-user, [class*="userName"], [class*="sn-user"]');
    // cookie 检测
    checks.has_session_cookie = document.cookie.includes('_tb_token_') ||
                                 document.cookie.includes('cookie2') ||
                                 document.cookie.includes('sgcookie');
    checks.is_logged_in = !checks.url_has_login &&
                          (checks.has_user || checks.has_session_cookie);
    return checks;
}
"""

JD_CHECK_LOGIN_JS = """
() => {
    const checks = {};
    const url = window.location.href;
    checks.url_has_login = url.includes('login.jd.com') ||
                           url.includes('passport.jd.com') ||
                           url.includes('plogin');
    // 京东登录后有用户昵称
    checks.has_user = !!document.querySelector('.nickname, .user-name, [class*="userName"], #ttbar-login .nickname');
    checks.has_session_cookie = document.cookie.includes('3AB9D23F7A4B3') ||
                                 document.cookie.includes('thor');
    checks.is_logged_in = !checks.url_has_login &&
                          (checks.has_user || checks.has_session_cookie);
    return checks;
}
"""

LOGIN_CHECK_JS_MAP = {
    "douyin": DOUYIN_CHECK_LOGIN_JS,
    "zhihu": ZHIHU_CHECK_LOGIN_JS,
    "xiaohongshu": XHS_CHECK_LOGIN_JS,
    "tmall": TMALL_CHECK_LOGIN_JS,
    "jd": JD_CHECK_LOGIN_JS,
}

HOMEPAGE_MAP = {
    "douyin": "https://www.douyin.com",
    "zhihu": "https://www.zhihu.com",
    "xiaohongshu": "https://www.xiaohongshu.com",
    "tmall": "https://www.tmall.com",
    "jd": "https://www.jd.com",
}


# ========== 核心登录流程 ==========

def ensure_session(page, platform: str, timeout_sec: int = 180) -> bool:
    """
    确保已登录。流程：
      1. 如果 session 有效 → 直接返回 True
      2. 打开平台首页，用 JS 检测登录状态
      3. 未登录 → 打印提示，等待用户在浏览器中操作，终端输入 yes 确认
      4. 登录成功 → 保存状态 → 返回 True

    Args:
        page: Playwright page 对象
        platform: "douyin" / "zhihu" / "xiaohongshu"
        timeout_sec: 等待用户登录的超时时间（秒）

    Returns:
        True = 已登录，False = 登录失败/超时
    """
    # 快速路径：session 有效
    if is_session_valid(platform):
        print(f"  ✅ {platform} session 有效（上次验证: {_load_state(platform).get('verified_date', '?')}），跳过登录")
        return True

    # 打开首页
    homepage = HOMEPAGE_MAP[platform]
    check_js = LOGIN_CHECK_JS_MAP[platform]

    print(f"  🔑 正在打开 {platform} 首页检测登录状态...")
    page.goto(homepage, timeout=30000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # JS 检测登录状态
    try:
        checks = page.evaluate(check_js)
    except Exception as e:
        print(f"  ⚠️  登录检测 JS 执行失败: {e}")
        checks = {"is_logged_in": False}

    if checks.get("is_logged_in"):
        print(f"  ✅ 检测到 {platform} 已登录，无需操作")
        mark_session_valid(platform)
        return True

    # 未登录，提示用户
    print()
    print("=" * 60)
    print(f"  🔑  需要登录 {platform}")
    print()
    print(f"  浏览器已打开 {platform} 首页，请手动登录：")
    print(f"    1. 在弹出的浏览器窗口中完成登录")
    print(f"    2. 确认页面显示已登录状态（能看到个人信息）")
    print(f"    3. 回到终端，输入 yes 并回车")
    print()
    print(f"  （超时: {timeout_sec} 秒）")
    print("=" * 60)
    print()

    # 等待用户输入确认
    import threading
    user_confirmed = threading.Event()

    def _wait_input():
        try:
            while True:
                user_input = input("  是否已完成登录？(输入 yes 继续): ").strip().lower()
                if user_input == "yes":
                    user_confirmed.set()
                    break
                elif user_input in ("quit", "exit", "q", "no"):
                    break
                print("    请输入 yes 以确认继续...")
        except EOFError:
            pass

    input_thread = threading.Thread(target=_wait_input, daemon=True)
    input_thread.start()

    # 等待用户确认或超时
    if not user_confirmed.wait(timeout=timeout_sec):
        print(f"\n  ⏰ 等待登录超时 ({timeout_sec}s)，尝试继续...")

    # 验证登录状态
    page.wait_for_timeout(2000)
    try:
        checks = page.evaluate(check_js)
        if checks.get("is_logged_in"):
            print(f"  ✅ {platform} 登录成功！session 已缓存，下次无需重新登录")
            mark_session_valid(platform)
            return True
    except Exception:
        pass

    if user_confirmed.is_set():
        # 用户确认了但 JS 检测没通过，也标记为有效（可能是 JS 检测不准确）
        print(f"  ✅ 用户确认登录完成，继续执行")
        mark_session_valid(platform)
        return True

    print(f"  ⚠️  未能确认登录状态，继续尝试...")
    mark_session_invalid(platform)
    return False


def check_and_login_if_needed(page, platform: str) -> bool:
    """
    运行中的登录检查（页面加载后调用）
    如果被重定向到登录页，提示用户登录
    """
    check_js = LOGIN_CHECK_JS_MAP.get(platform)
    if not check_js:
        return True

    try:
        checks = page.evaluate(check_js)
        if checks.get("is_logged_in"):
            return True
    except Exception:
        pass

    # 检测到未登录
    print(f"\n  ⚠️  检测到 {platform} 未登录或 session 已过期")
    print(f"  请在浏览器中完成登录，然后输入 yes 继续...")

    try:
        while True:
            user_input = input("  是否已完成登录？(输入 yes 继续): ").strip().lower()
            if user_input == "yes":
                page.wait_for_timeout(2000)
                mark_session_valid(platform)
                return True
            elif user_input in ("quit", "exit", "q"):
                return False
    except EOFError:
        return False


# ========== 便捷函数 ==========

def print_session_status():
    """打印所有平台的 session 状态"""
    print("\n  📋 登录 Session 状态:")
    print("  " + "-" * 50)
    for platform in ["douyin", "zhihu", "xiaohongshu", "tmall", "jd"]:
        profile = get_profile_dir(platform)
        has_profile = (profile / "Default").exists()
        state = _load_state(platform)
        valid = is_session_valid(platform)

        status = "✅ 有效" if valid else ("⚠️ 已过期" if has_profile else "❌ 未登录")
        verified = state.get("verified_date", "从未验证")
        print(f"  {platform:12s}  {status}  (验证时间: {verified})")
    print()


if __name__ == "__main__":
    print_session_status()
