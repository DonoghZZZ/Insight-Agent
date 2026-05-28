"""
智能分析调度器 - 实现"专业工具优先"策略

核心逻辑：
1. 用户提出分析需求
2. 系统匹配专业工具
3. 有匹配工具 → 使用专业工具（快速、可靠）
4. 无匹配工具 → 调用大模型（灵活、通用）
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from analysis.tools_registry import (
    ToolsRegistry, AnalysisCategory, AnalysisTool,
    execute_tool, recommend_tools
)

logger = logging.getLogger(__name__)


@dataclass
class AnalysisRequest:
    """分析请求"""
    user_query: str  # 用户原始查询
    intent: str  # 解析出的意图
    required_fields: List[str]  # 需要的字段类型
    confidence: float  # 意图识别置信度


@dataclass
class AnalysisResult:
    """分析结果"""
    tool_name: str  # 使用的工具
    source: str  # 来源："builtin" 或 "llm"
    result: Dict[str, Any]  # 分析结果
    execution_time: float  # 执行时间
    success: bool  # 是否成功


class SmartAnalyzer:
    """智能分析调度器"""

    def __init__(self, data: List[Dict], data_file: Path):
        self.data = data
        self.data_file = data_file
        self.available_tools = ToolsRegistry.get_all_tools()

    def analyze(self, user_query: str) -> AnalysisResult:
        """
        智能分析入口

        Args:
            user_query: 用户查询（如"帮我做情感分析"）

        Returns:
            AnalysisResult: 分析结果
        """
        import time
        start_time = time.time()

        # 1. 解析用户意图
        request = self._parse_intent(user_query)
        logger.info(f"解析意图: {request.intent} (置信度: {request.confidence:.2f})")

        # 2. 尝试匹配专业工具
        matched_tool = self._find_matching_tool(request)

        if matched_tool:
            # 3a. 使用专业工具
            logger.info(f"使用专业工具: {matched_tool.name}")
            result = execute_tool(matched_tool.name, self.data, self.data_file)

            return AnalysisResult(
                tool_name=matched_tool.name,
                source="builtin",
                result=result,
                execution_time=time.time() - start_time,
                success="error" not in result
            )
        else:
            # 3b. 调用大模型
            logger.info("无匹配专业工具，调用大模型")
            result = self._call_llm_fallback(user_query)

            return AnalysisResult(
                tool_name="llm_fallback",
                source="llm",
                result=result,
                execution_time=time.time() - start_time,
                success="error" not in result
            )

    def _parse_intent(self, user_query: str) -> AnalysisRequest:
        """解析用户意图"""
        query_lower = user_query.lower()

        # 关键词映射到意图
        intent_mapping = {
            # 基础统计
            "统计": "basic_stats",
            "描述": "basic_stats",
            "概览": "basic_stats",
            "基础": "basic_stats",
            "均值": "basic_stats",
            "中位数": "basic_stats",
            "分布": "basic_stats",

            # 情感分析
            "情感": "sentiment_analysis",
            "情绪": "sentiment_analysis",
            "正负面": "sentiment_analysis",
            "满意度": "sentiment_analysis",
            "态度": "sentiment_analysis",

            # 词频统计
            "词频": "word_frequency",
            "关键词": "word_frequency",
            "分词": "word_frequency",
            "tfidf": "word_frequency",
            "高频": "word_frequency",

            # 时间序列
            "时间": "time_series",
            "趋势": "time_series",
            "周期": "time_series",
            "按日": "time_series",
            "按周": "time_series",
            "按月": "time_series",

            # 主题提取
            "主题": "theme_extraction",
            "话题": "theme_extraction",
            "核心": "theme_extraction",

            # 内容分类
            "分类": "content_category",
            "归类": "content_category",
            "类别": "content_category",

            # 观点挖掘
            "观点": "insight_mining",
            "反馈": "insight_mining",
            "建议": "insight_mining",
            "需求": "insight_mining",
            "问题": "insight_mining",
        }

        # 匹配意图
        matched_intent = None
        max_confidence = 0.0

        for keyword, intent in intent_mapping.items():
            if keyword in query_lower:
                confidence = 0.9 if len(keyword) > 2 else 0.7
                if confidence > max_confidence:
                    max_confidence = confidence
                    matched_intent = intent

        # 如果没有匹配，使用通用意图
        if not matched_intent:
            matched_intent = "general_analysis"
            max_confidence = 0.5

        # 推断需要的字段类型
        required_fields = self._infer_required_fields(matched_intent)

        return AnalysisRequest(
            user_query=user_query,
            intent=matched_intent,
            required_fields=required_fields,
            confidence=max_confidence
        )

    def _infer_required_fields(self, intent: str) -> List[str]:
        """推断需要的字段类型"""
        field_mapping = {
            "basic_stats": [],
            "sentiment_analysis": ["text"],
            "word_frequency": ["text"],
            "time_series": ["date"],
            "theme_extraction": ["text"],
            "content_category": ["text"],
            "insight_mining": ["text"],
        }
        return field_mapping.get(intent, [])

    def _find_matching_tool(self, request: AnalysisRequest) -> Optional[AnalysisTool]:
        """查找匹配的专业工具"""
        # 1. 精确匹配
        tool = ToolsRegistry.get_tool(request.intent)
        if tool:
            # 检查数据是否满足要求
            if self._check_data_requirements(tool):
                return tool

        # 2. 模糊匹配
        tools = ToolsRegistry.search_tools(request.user_query)
        for tool in tools:
            if self._check_data_requirements(tool):
                return tool

        # 3. 推荐匹配
        recommended = ToolsRegistry.get_tools_for_data(self.data)
        if recommended and request.confidence > 0.7:
            # 如果意图明确，返回第一个推荐工具
            return recommended[0]

        return None

    def _check_data_requirements(self, tool: AnalysisTool) -> bool:
        """检查数据是否满足工具要求"""
        if not tool.required_fields:
            return True

        from analysis.quantitative import auto_detect_fields
        field_types = auto_detect_fields(self.data)

        has_text = any(t == "text" for t in field_types.values())
        has_numeric = any(t == "numeric" for t in field_types.values())
        has_date = any(t == "date" for t in field_types.values())

        for req in tool.required_fields:
            if req == "text" and not has_text:
                return False
            elif req == "numeric" and not has_numeric:
                return False
            elif req == "date" and not has_date:
                return False

        return True

    def _call_llm_fallback(self, user_query: str) -> Dict[str, Any]:
        """调用大模型作为兜底"""
        try:
            from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
            from openai import OpenAI

            client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

            # 构建系统提示
            system_prompt = self._build_llm_system_prompt()

            # 调用 LLM
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                max_tokens=2048,
                temperature=0.3,
            )

            result_text = response.choices[0].message.content

            # 尝试解析为 JSON
            import json
            try:
                # 提取 JSON 部分
                if "```json" in result_text:
                    json_str = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    json_str = result_text.split("```")[1].split("```")[0]
                else:
                    json_str = result_text

                result = json.loads(json_str.strip())
                return {"analysis": result, "raw_response": result_text}
            except json.JSONDecodeError:
                return {"analysis": result_text, "raw_response": result_text}

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return {"error": f"LLM 分析失败: {e}"}

    def _build_llm_system_prompt(self) -> str:
        """构建 LLM 系统提示"""
        # 获取可用工具描述
        tools_desc = ToolsRegistry.generate_tools_description()

        # 获取数据概览
        from analysis.quantitative import auto_detect_fields
        field_types = auto_detect_fields(self.data)
        fields_desc = "\n".join(f"- {f} ({t})" for f, t in field_types.items())

        return f"""你是 Insight Agent 的智能分析助手。

## 数据概览
- 记录数: {len(self.data)} 条
- 字段数: {len(self.data[0]) if self.data else 0} 个

### 字段类型
{fields_desc}

## 可用专业工具
{tools_desc}

## 分析策略

当用户提出分析需求时：

1. **优先使用专业工具**：如果用户需求匹配上述工具，直接使用
2. **组合分析**：可以组合多个工具进行综合分析
3. **自定义分析**：如果没有匹配工具，使用 Python 代码进行分析

## 输出格式

对于专业工具，输出：
```json
{{
  "tool": "工具名",
  "parameters": {{}},
  "reason": "选择理由"
}}
```

对于自定义分析，输出：
```json
{{
  "code": "Python 代码",
  "description": "分析说明",
  "expected_output": "预期输出"
}}
```

## 注意事项
- 数据文件路径: {self.data_file}
- 字段名如上述列表所示（可能是中文）
- 结果用 print() 输出，清晰标注
- 优先使用 jieba、snownlp 等已安装的库
"""


def smart_analyze(data: List[Dict], data_file: Path, user_query: str) -> AnalysisResult:
    """智能分析入口函数"""
    analyzer = SmartAnalyzer(data, data_file)
    return analyzer.analyze(user_query)


def get_analysis_suggestions(data: List[Dict]) -> List[Dict[str, Any]]:
    """获取分析建议"""
    analyzer = SmartAnalyzer(data, Path("dummy.csv"))
    tools = analyzer.available_tools

    # 根据数据推荐工具
    recommended = recommend_tools(data)

    suggestions = []
    for tool_name in recommended:
        tool = ToolsRegistry.get_tool(tool_name)
        if tool:
            suggestions.append({
                "name": tool.name,
                "category": tool.category.value,
                "description": tool.description,
                "examples": tool.examples,
                "priority": tool.priority,
            })

    return suggestions
