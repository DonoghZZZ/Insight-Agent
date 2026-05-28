"""AI 分析模块 — 基于 Agent 内核架构

AI 直接主持分析全过程：预览数据 → 打招呼 → 动态跑代码 → 呈现结论 → 持续对话
"""

import json
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_MAX_TOKENS, OUTPUT_DIR

logger = logging.getLogger(__name__)

# 会话存储目录
SESSION_DIR = OUTPUT_DIR / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

_AGENT_LOADED = False


def _ensure_agent():
    """确保 Agent 内核已加载"""
    global _AGENT_LOADED
    if _AGENT_LOADED:
        return

    core_path = Path(__file__).parent.parent / "agent_core"

    # 多个可能的路径
    possible_paths = [
        core_path,
        core_path / "hermes",
        core_path / "src",
    ]

    for path in possible_paths:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))

    _AGENT_LOADED = True
    logger.info(f"Agent 内核路径已加载: {core_path}")


class InsightAnalyst:
    """AI 数据分析师 — 接收原始数据，动态分析，持续对话"""

    def __init__(self, data: list, data_file: Path):
        self.data = data
        self.data_file = data_file
        self.record_count = len(data)
        self.columns = list(data[0].keys()) if data else []

        _ensure_agent()

        # 尝试多种方式导入 Agent
        self.agent = None
        try:
            from run_agent import AIAgent
            self.agent = AIAgent(
                api_key=LLM_API_KEY,
                base_url=LLM_BASE_URL,
                model=LLM_MODEL,
                provider="deepseek",
                enabled_toolsets=["file", "terminal", "web"],
                max_iterations=30,
                quiet_mode=False,
                skip_context_files=True,
                skip_memory=True,
            )
            logger.info("Agent 内核加载成功")
        except ImportError as e:
            logger.warning(f"无法加载完整 Agent 内核: {e}，将使用简化模式")
            self.agent = None
        except Exception as e:
            logger.error(f"Agent 初始化失败: {e}")
            self.agent = None

        self._system_msg = self._build_prompt()

    def _build_prompt(self) -> str:
        """构建分析师的系统提示词"""
        # 字段信息
        from analysis.quantitative import auto_detect_fields
        field_types = auto_detect_fields(self.data)
        fields_desc = "\n".join(
            f"  - {f} ({t})" for f, t in field_types.items()
        )

        # 前5行样本
        sample_rows = []
        for i, row in enumerate(self.data[:5]):
            items = ", ".join(f"{k}={str(row.get(k,''))[:30]}" for k in list(self.columns)[:6])
            sample_rows.append(f"  [{i+1}] {items}")

        # 获取可用工具描述
        try:
            from analysis.tools_registry import get_tools_description_for_ai
            tools_description = get_tools_description_for_ai()
        except ImportError:
            tools_description = "工具注册表不可用"

        # 获取推荐工具
        try:
            from analysis.tools_registry import recommend_tools
            recommended = recommend_tools(self.data)
            recommended_desc = ", ".join(recommended) if recommended else "无"
        except ImportError:
            recommended_desc = "不可用"

        return f"""你是 Insight Agent 的 AI 数据分析师，服务于Insight Agent数据分析系统。

## 📊 当前数据

**文件**: {self.data_file.name}
**记录数**: {self.record_count} 条
**字段数**: {len(self.columns)} 个

### 字段及类型
{fields_desc}

### 前5行样本
{chr(10).join(sample_rows)}

## 🎯 你的角色

你是主动的数据分析师，不是被动问答机。有以下能力：

### 优先使用专业工具（推荐）
{tools_description}

### 根据当前数据推荐的工具
{recommended_desc}

### 其他能力
- **terminal 工具**: 执行 Python 脚本做任意分析（jieba分词、情感分析、统计、可视化等）
- **file 工具**: 读取数据文件做更细粒度检查
- **web 工具**: 联网查背景知识

## 📋 行为规范

### 核心原则：专业工具优先

当用户提出分析需求时：

1. **首先检查是否有匹配的专业工具**
   - 查看上述工具列表
   - 如果有匹配工具，直接使用
   - 使用方式：调用 `execute_tool(tool_name, data, data_file)`

2. **如果没有匹配工具，再使用大模型**
   - 使用 terminal 工具执行 Python 代码
   - 或调用 LLM 进行复杂分析

3. **工具使用示例**
   ```python
   from analysis.tools_registry import execute_tool
   result = execute_tool("sentiment_analysis", data, data_file)
   print(result)
   ```

### 第一步（打招呼）

用户说"开始分析"后，你应该：

1. 先简要描述数据概览（字段、类型、规模）
2. 列出可用的专业工具（从工具注册表获取）
3. 根据数据字段类型，标注哪些工具适用（✅）、哪些不适用（❌）
4. 提出2-3个推荐组合（如"新手套餐：基础统计+情感分析+词频"）
5. 询问用户想从哪个开始，或直接按推荐执行

### 后续对话

- 用户指定方向后，优先使用专业工具
- 如果没有匹配工具，再写 Python 代码或调用 LLM
- 分析结果用表格或结构化文本呈现
- 主动发现数据中的规律和异常
- 完成一个分析后，提出下一步建议

### 代码规范

- 数据文件路径: {self.data_file}
- 字段名如上述字段列表所示（中文）
- 结果用 print() 输出，清晰标注
- 优先使用专业工具，其次才是自定义代码

## 语言风格
- 专业但亲切，像同事讨论数据
- 中文回复
- 主动、有洞察力
- 明确说明使用了哪个工具"""

    def greet_and_analyze(self) -> str:
        """AI 首次打招呼 + 初步分析"""
        return self.chat("开始分析")

    def chat(self, message: str) -> str:
        """对话（流式输出）"""
        # 流式回调：逐 token 打印到终端
        def stream_token(token: str):
            if token:
                print(token, end="", flush=True)

        try:
            # 如果 Agent 加载成功，使用完整模式
            if self.agent is not None:
                result = self.agent.run_conversation(
                    user_message=message,
                    system_message=self._system_msg,
                    stream_callback=stream_token,
                )
                if isinstance(result, dict):
                    return result.get("final_response", str(result))
                return str(result)
            else:
                # 简化模式：直接调用 LLM API
                return self._simple_chat(message)
        except Exception as e:
            logger.error(f"对话出错: {e}")
            return f"❌ 出错: {e}"

    def _simple_chat(self, message: str) -> str:
        """简化模式的对话（当 Agent 内核不可用时）"""
        from openai import OpenAI

        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

        # 构建消息
        messages = [
            {"role": "system", "content": self._system_msg},
            {"role": "user", "content": message}
        ]

        try:
            # 流式输出
            print("  ", end="", flush=True)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                stream=True,
                max_tokens=LLM_MAX_TOKENS,
                temperature=0.7,
            )

            full_response = []
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    full_response.append(content)

            print()  # 换行
            return "".join(full_response)
        except Exception as e:
            return f"❌ API 调用失败: {e}"


class AnalystSession:
    """分析师会话管理 — 支持持久化"""

    def __init__(self, data: list, data_file: Path, session_id: str = None):
        self.analyst = InsightAnalyst(data, data_file)
        self.data_file = data_file
        self.history = []
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")

    def process_message(self, message: str) -> str:
        if message.strip().lower() in ("exit", "quit", "q", "退出"):
            self.save()  # 退出时自动保存
            return "__EXIT__"
        if message.strip().lower() in ("help", "帮助", "?"):
            return self._help_text()

        resp = self.analyst.chat(message)
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": resp})
        return resp

    def save(self):
        """保存会话到磁盘"""
        try:
            session_file = SESSION_DIR / f"{self.session_id}.json"
            data = {
                "session_id": self.session_id,
                "data_file": str(self.data_file),
                "history": self.history,
                "saved_at": datetime.now().isoformat(),
            }
            session_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def list_sessions() -> List[Dict]:
        """列出所有已保存的会话"""
        sessions = []
        for f in sorted(SESSION_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                msg_count = len(data.get("history", [])) // 2
                data_file = data.get("data_file", "?")
                sessions.append({
                    "id": data["session_id"],
                    "file": data_file,
                    "messages": msg_count,
                    "saved": data.get("saved_at", "")[:16],
                })
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"会话文件格式错误 {f.name}: {e}")
                continue
            except Exception as e:
                logger.error(f"读取会话文件失败 {f.name}: {e}")
                continue
        return sessions[:10]

    @staticmethod
    def load_session(session_id: str):
        """从磁盘恢复会话"""
        session_file = SESSION_DIR / f"{session_id}.json"
        if not session_file.exists():
            return None
        data = json.loads(session_file.read_text(encoding="utf-8"))
        data_file = Path(data["data_file"])
        if not data_file.exists():
            return None
        return data, data_file

    def _help_text(self) -> str:
        return """📋 可用操作：
  • 直接说出你想分析的方向，AI会自动写代码执行
  • 例如："帮我做情感分析" / "统计词频" / "看看趋势"
  • AI 会主动发现规律、给出建议
  • 输入 exit / q / 退出  结束对话（自动保存）
  • 输入 help / 帮助 显示此信息"""
