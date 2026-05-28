# Insight Agent CLI 使用指南

## 🚀 快速开始

### 安装和启动

```bash
# 进入项目目录
cd insight-agent

# 方式一：使用快速启动脚本
./insight

# 方式二：使用 Python
python main.py

# 方式三：使用 CLI 增强器
python tools/cli_enhancer.py
```

---

## 📋 命令列表

### 核心命令

| 命令 | 快捷键 | 描述 | 示例 |
|------|--------|------|------|
| `crawl` | `c` | 数据爬取 | `crawl zhihu` |
| `analyze` | `a` | 数据分析 | `analyze data.csv` |
| `chat` | `ch` | AI 对话 | `chat` |
| `web` | `w` | Web UI | `web` |
| `report` | `r` | 生成报告 | `report data.csv` |
| `tools` | `t` | 查看工具 | `tools` |
| `validate` | `v` | 验证系统 | `validate` |
| `help` | `h` | 显示帮助 | `help crawl` |
| `exit` | `q` | 退出程序 | `exit` |

---

## 🎯 常用操作

### 1. 数据爬取

```bash
# 启动爬虫
insight crawl

# 或使用快捷键
insight c

# 指定平台
insight crawl zhihu
insight crawl bilibili
insight crawl xiaohongshu
```

**支持平台**：
- 知乎 (zhihu)
- B站 (bilibili)
- 小红书 (xiaohongshu)
- 抖音 (douyin)
- 知网 (cnki)
- 天猫 (tmall)
- 京东 (jd)
- 豆瓣 (douban)

### 2. 数据分析

```bash
# 启动分析
insight analyze

# 分析指定文件
insight analyze data.csv

# 使用模板
insight analyze --template sentiment
insight analyze --template word_freq
```

**分析模板**：
- `sentiment` - 情感分析
- `word_freq` - 词频统计
- `stats` - 基础统计
- `time` - 时间序列
- `theme` - 主题提取

### 3. AI 对话

```bash
# 启动 AI 对话
insight chat

# 指定数据文件
insight chat --file data.csv

# 示例对话
你: 帮我做情感分析
AI: 好的，我来分析数据的情感倾向...
```

**智能分析优先级**：
1. ✅ 优先使用专业工具（快速、可靠）
2. ⚠️ 无匹配时调用大模型（灵活、通用）

### 4. Web UI

```bash
# 启动 Web UI
insight web

# 指定端口
insight web --port 8080

# 后台运行
insight web --background
```

**访问地址**：http://localhost:9527

### 5. 查看工具

```bash
# 查看所有工具
insight tools

# 按类别筛选
insight tools --category text
insight tools --category quantitative
```

**工具类别**：
- `quantitative` - 定量分析
- `text_analysis` - 文本分析
- `time_series` - 时间序列
- `qualitative` - 定性分析

### 6. 验证系统

```bash
# 运行系统验证
insight validate

# 验证内容：
# ✅ 配置验证
# ✅ 模块验证
# ✅ 工具验证
# ✅ 分析验证
# ✅ Web 验证
```

---

## 💡 使用技巧

### 1. 命令自动补全

在交互模式中，输入命令的前几个字母，按 Tab 键自动补全：

```bash
Insight › cr<TAB>
Insight › crawl
```

### 2. 命令历史

使用上下箭头键浏览历史命令：

```bash
Insight › [上箭头]  # 上一条命令
Insight › [下箭头]  # 下一条命令
```

### 3. 快捷键

使用快捷键快速执行命令：

```bash
Insight › c          # 等同于 crawl
Insight › a          # 等同于 analyze
Insight › ch         # 等同于 chat
Insight › w          # 等同于 web
```

### 4. 参数传递

命令支持参数传递：

```bash
Insight › crawl zhihu --max 100
Insight › analyze data.csv --template sentiment
Insight › web --port 8080 --background
```

---

## 🔧 高级用法

### 1. 批量操作

```bash
# 批量分析多个文件
insight analyze file1.csv file2.csv file3.csv

# 批量生成报告
insight report file1.csv file2.csv
```

### 2. 管道操作

```bash
# 从标准输入读取数据
cat data.csv | insight analyze

# 输出到文件
insight analyze data.csv > result.txt
```

### 3. 脚本集成

```bash
#!/bin/bash
# 自动化脚本

# 爬取数据
insight crawl zhihu --max 100

# 分析数据
insight analyze output/zhihu_*.csv

# 生成报告
insight report output/zhihu_*.csv

# 启动 Web UI
insight web --background
```

---

## 📊 工具系统

### 可用工具

| 工具 | 类别 | 描述 | 需要字段 |
|------|------|------|----------|
| `basic_stats` | 定量 | 基础统计 | 任意 |
| `sentiment_analysis` | 文本 | 情感分析 | text |
| `word_frequency` | 文本 | 词频统计 | text |
| `time_series` | 时间 | 时间序列 | date |
| `theme_extraction` | 定性 | 主题提取 | text |
| `content_category` | 定性 | 内容分类 | text |
| `insight_mining` | 定性 | 观点挖掘 | text |

### 工具使用示例

```python
from analysis.tools_registry import execute_tool
from pathlib import Path

data = [
    {"content": "这个产品非常好", "score": "85"},
    {"content": "体验很差", "score": "45"},
]

# 执行情感分析
result = execute_tool("sentiment_analysis", data, Path("data.csv"))
print(result)

# 执行基础统计
result = execute_tool("basic_stats", data, Path("data.csv"))
print(result)
```

---

## 🎨 界面预览

### CLI 界面

```
╭──────────────────────────────────────╮
│ 🚀 Insight Agent CLI                    │
│                                      │
│ 智能数据分析工具 - 专业工具优先      │
│                                      │
│ 输入 help 查看所有命令               │
│ 输入 exit 退出程序                   │
╰──────────────────────────────────────╯

Insight › tools

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ 工具名称       ┃ 类别       ┃ 描述               ┃ 需要字段 ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ basic_stats    │ quantita.. │ 基础统计分析：计.. │ 任意     │
│ sentiment_ana..│ text_analysis │ 情感分析：使用.. │ text     │
│ word_frequency │ text_analysis │ 词频统计：使用.. │ text     │
└────────────────┴────────────┴────────────────────┴──────────┘

Insight ›
```

---

## 🐛 故障排除

### 问题 1：命令未找到

```
bash: nku: command not found
```

**解决方案**：
```bash
# 确保脚本有执行权限
chmod +x insight

# 或使用 Python 直接运行
python tools/cli_enhancer.py
```

### 问题 2：模块导入失败

```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**：
```bash
# 安装依赖
pip install -r requirements.txt

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 问题 3：工具执行失败

```
Error: 工具执行失败
```

**解决方案**：
```bash
# 验证系统
insight validate

# 查看日志
tail -f output/app.log

# 检查数据格式
insight tools
```

---

## 📚 相关文档

- [README.md](../README.md) - 项目概述
- [ANALYSIS_TOOLS_GUIDE.md](ANALYSIS_TOOLS_GUIDE.md) - 分析工具指南
- [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) - Web UI 指南

---

## 🎉 总结

**Insight Agent CLI** 提供了：

✅ **丰富的命令**：覆盖所有核心功能  
✅ **智能补全**：快速输入命令  
✅ **快捷键**：高效操作  
✅ **交互式向导**：友好提示  
✅ **专业工具优先**：快速可靠  

**立即开始**：
```bash
./insight
# 或
python main.py
```

---

**CLI 版本**: v1.0  
**最后更新**: 2024-01-27
