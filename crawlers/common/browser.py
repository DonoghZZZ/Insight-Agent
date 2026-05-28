#!/usr/bin/env python3
"""
浏览器反检测配置模块

为各平台爬虫提供统一的：
- 反检测 JS 注入脚本
- 浏览器启动参数
- 默认视口和 User-Agent
"""

# Chrome User-Agent（保持更新）
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# 默认视口大小
DEFAULT_VIEWPORT = {"width": 1280, "height": 900}

# Chromium 启动参数（反检测 + 稳定性）
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-popup-blocking",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    "--disable-ipc-flooding-protection",
    "--password-store=basic",
]

# 反检测 JavaScript（注入到每个页面）
# 移除 navigator.webdriver 标记，伪装为正常浏览器
STEALTH_JS = """
// 移除 webdriver 标记
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// 伪装 plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
        {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''},
    ],
});

// 伪装 languages
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en-US', 'en']});

// 伪装 platform
Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});

// 移除 Chrome 自动化相关属性
if (window.chrome) {
    window.chrome.runtime = {};
} else {
    window.chrome = {runtime: {}};
}

// 伪装 permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : originalQuery(parameters);

// 隐藏 automation 标签
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

// WebGL 指纹伪装
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
};
"""