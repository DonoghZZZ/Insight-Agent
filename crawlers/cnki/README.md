# 知网爬虫 - 安装指南

## 系统检测

**您的系统上没有检测到以下浏览器：**
- ❌ Google Chrome
- ❌ Mozilla Firefox  
- ❌ Safari
- ❌ Microsoft Edge

---

## 安装浏览器 (二选一)

### 方法1: 安装 Chrome (推荐)

**macOS:**
```bash
# 使用Homebrew安装
brew install --cask google-chrome
```

**或者手动下载:**
1. 访问 https://www.google.com/chrome/
2. 下载并安装 Chrome

### 方法2: 安装 Firefox (备选)

**macOS:**
```bash
brew install --cask firefox
```

---

## 安装Python依赖

```bash
cd ~/Desktop/CNKI_Spider
pip install -r requirements.txt
```

如果安装selenium失败，单独安装:
```bash
pip install selenium webdriver-manager
```

---

## 启动爬虫

```bash
# 方法1: 使用一键启动器
cd ~/Desktop/CNKI_Spider
python3 launcher.py

# 方法2: 使用命令行
python3 main.py search "你的关键词" -p 3
```

---

## 常见问题

### Q: 提示 "Selenium未安装"
```bash
pip install selenium
```

### Q: 提示 "ChromeDriver错误"
```bash
pip install webdriver-manager
```
webdriver-manager会自动下载匹配的ChromeDriver

### Q: 浏览器窗口闪退
确保已安装浏览器，然后重试

### Q: 搜索返回0条结果
1. 检查关键词是否正确
2. 检查网络连接
3. 可能是知网页面结构更新，需要更新选择器

---

## 注意事项

⚠️ 请仅用于学术研究目的  
⚠️ 合理控制请求频率，避免封IP
