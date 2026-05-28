# 贡献指南

感谢你对 Insight Agent 项目的关注！我们欢迎任何形式的贡献。

## 📋 目录

- [开始之前](#开始之前)
- [如何贡献](#如何贡献)
- [开发环境](#开发环境)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [问题反馈](#问题反馈)

## 开始之前

在开始贡献之前，请确保：

1. 阅读并理解项目 [README.md](README.md)
2. 查看 [CHANGELOG.md](CHANGELOG.md) 了解最新更新
3. 检查 [Issues](https://github.com/your-org/insight-agent/issues) 是否已有相关问题

## 如何贡献

### 报告 Bug

1. 使用 [Bug Report 模板](https://github.com/your-org/insight-agent/issues/new?template=bug_report.md)
2. 提供详细的复现步骤
3. 包含错误日志和截图（如有）

### 提出新功能

1. 使用 [Feature Request 模板](https://github.com/your-org/insight-agent/issues/new?template=feature_request.md)
2. 说明使用场景和需求
3. 提供可能的实现方案

### 提交代码

1. Fork 项目仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 开发环境

### 环境准备

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/insight-agent.git
cd insight-agent

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. 安装 pre-commit hooks
pre-commit install
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行带覆盖率的测试
pytest tests/ -v --cov=analysis --cov=validator --cov-report=html

# 运行特定测试文件
pytest tests/test_config.py -v

# 运行特定测试类
pytest tests/test_config.py::TestConfigValidator -v

# 运行特定测试方法
pytest tests/test_config.py::TestConfigValidator::test_validate_returns_tuple -v
```

### 代码检查

```bash
# 运行 linter
flake8 analysis/ validator/ chat/

# 检查代码格式
black --check analysis/ validator/ chat/

# 自动格式化代码
black analysis/ validator/ chat/

# 排序 import
isort analysis/ validator/ chat/

# 类型检查
mypy analysis/ validator/ chat/
```

## 代码规范

### Python 风格

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 规范
- 使用 [Black](https://github.com/psf/black) 进行代码格式化
- 最大行宽：120 字符
- 使用类型注解（可选但推荐）

### 命名规范

- **变量和函数**：小写字母 + 下划线 (`snake_case`)
- **类**：大写字母开头 (`CamelCase`)
- **常量**：全大写 + 下划线 (`UPPER_CASE`)
- **私有成员**：单下划线开头 (`_private`)

### 文档字符串

使用 Google 风格的文档字符串：

```python
def function_name(param1: str, param2: int) -> bool:
    """
    函数功能简述

    Args:
        param1: 参数1的说明
        param2: 参数2的说明

    Returns:
        返回值的说明

    Raises:
        ValueError: 异常情况说明

    Examples:
        >>> function_name("test", 123)
        True
    """
    pass
```

### 注释规范

- 使用中文注释（项目语言）
- 复杂逻辑必须添加注释
- 避免无意义的注释
- 保持注释与代码同步

```python
# ✅ 好的注释
# 使用 TF-IDF 算法提取关键词，权重越高表示越重要
keywords = extract_tfidf(texts)

# ❌ 不好的注释
# 提取关键词
keywords = extract_tfidf(texts)
```

## 提交规范

### Commit Message 格式

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具链更新

**示例**：

```
feat(analysis): 添加情感分析功能

- 使用 SnowNLP 进行情感打分
- 支持正面/中性/负面分类
- 添加情感分布可视化

Closes #123
```

### Pull Request 规范

1. **标题**：简洁明了，使用英文
2. **描述**：详细说明改动内容
3. **关联 Issue**：使用 `Closes #123` 格式
4. **测试**：确保所有测试通过
5. **文档**：更新相关文档

## 问题反馈

### 提问方式

1. 使用 [GitHub Discussions](https://github.com/your-org/insight-agent/discussions)
2. 提供详细的上下文信息
3. 包含错误日志和复现步骤
4. 使用清晰的标题

### 反馈渠道

- **Bug 报告**：[GitHub Issues](https://github.com/your-org/insight-agent/issues)
- **功能建议**：[GitHub Issues](https://github.com/your-org/insight-agent/issues)
- **一般讨论**：[GitHub Discussions](https://github.com/your-org/insight-agent/discussions)

## 行为准则

### 我们的承诺

为了营造一个开放和友好的环境，我们承诺：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

### 不当行为

以下行为是不被接受的：

- 使用性暗示的语言或图像
- 恶意评论或人身攻击
- 公开或私下骚扰
- 未经许可发布他人的私人信息
- 其他不道德或不专业的行为

## 许可证

贡献即表示你同意你的贡献将在 [MIT 许可证](LICENSE) 下发布。

## 致谢

感谢所有为项目做出贡献的人！

---

**最后更新**：2024-01-27
