"""
分析工具注册表 - 管理所有可用的分析工具

设计理念：
1. 专业工具优先：先用预定义的分析方法
2. 大模型兜底：没有现成方法时才调用 LLM
3. 工具分类清晰：按分析类型组织
4. 易于扩展：新工具只需注册即可
"""

import logging
from typing import Dict, List, Any, Callable, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisCategory(Enum):
    """分析类别"""
    QUANTITATIVE = "quantitative"  # 定量分析
    QUALITATIVE = "qualitative"    # 定性分析
    VISUALIZATION = "visualization"  # 可视化
    TEXT_ANALYSIS = "text_analysis"  # 文本分析
    TIME_SERIES = "time_series"    # 时间序列
    ADVANCED = "advanced"          # 高级分析


@dataclass
class AnalysisTool:
    """分析工具定义"""
    name: str
    category: AnalysisCategory
    description: str
    function: Callable
    required_fields: List[str]  # 需要的字段类型
    output_type: str  # 输出类型
    priority: int = 0  # 优先级，越高越优先
    examples: List[str] = None  # 示例用途

    def __post_init__(self):
        if self.examples is None:
            self.examples = []


class ToolsRegistry:
    """工具注册表"""

    _instance = None
    _tools: Dict[str, AnalysisTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    @classmethod
    def register(cls, tool: AnalysisTool):
        """注册工具"""
        cls._tools[tool.name] = tool
        logger.info(f"注册分析工具: {tool.name} ({tool.category.value})")

    @classmethod
    def get_tool(cls, name: str) -> Optional[AnalysisTool]:
        """获取工具"""
        return cls._tools.get(name)

    @classmethod
    def get_tools_by_category(cls, category: AnalysisCategory) -> List[AnalysisTool]:
        """按类别获取工具"""
        return [t for t in cls._tools.values() if t.category == category]

    @classmethod
    def get_all_tools(cls) -> List[AnalysisTool]:
        """获取所有工具"""
        return list(cls._tools.values())

    @classmethod
    def search_tools(cls, query: str) -> List[AnalysisTool]:
        """搜索工具"""
        query_lower = query.lower()
        results = []
        for tool in cls._tools.values():
            if (query_lower in tool.name.lower() or
                query_lower in tool.description.lower() or
                any(query_lower in ex.lower() for ex in tool.examples)):
                results.append(tool)
        return sorted(results, key=lambda t: t.priority, reverse=True)

    @classmethod
    def get_tools_for_data(cls, data: List[Dict]) -> List[AnalysisTool]:
        """根据数据特征推荐工具"""
        if not data:
            return []

        # 检测字段类型
        from analysis.quantitative import auto_detect_fields
        field_types = auto_detect_fields(data)

        has_text = any(t == "text" for t in field_types.values())
        has_numeric = any(t == "numeric" for t in field_types.values())
        has_date = any(t == "date" for t in field_types.values())

        recommended = []
        for tool in cls._tools.values():
            # 检查工具是否适用于当前数据
            if tool.required_fields:
                applicable = True
                for req in tool.required_fields:
                    if req == "text" and not has_text:
                        applicable = False
                        break
                    elif req == "numeric" and not has_numeric:
                        applicable = False
                        break
                    elif req == "date" and not has_date:
                        applicable = False
                        break
                if applicable:
                    recommended.append(tool)
            else:
                recommended.append(tool)

        return sorted(recommended, key=lambda t: t.priority, reverse=True)

    @classmethod
    def generate_tools_description(cls) -> str:
        """生成工具描述（供 AI 使用）"""
        tools = cls.get_all_tools()
        if not tools:
            return "暂无可用工具"

        # 按类别组织
        categories = {}
        for tool in tools:
            cat = tool.category.value
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tool)

        description = "## 可用分析工具\n\n"
        for cat_name, cat_tools in categories.items():
            description += f"### {cat_name.upper()}\n\n"
            for tool in cat_tools:
                description += f"- **{tool.name}**: {tool.description}\n"
                if tool.examples:
                    description += f"  示例: {', '.join(tool.examples[:3])}\n"
            description += "\n"

        return description


# ==================== 注册内置工具 ====================

def _register_builtin_tools():
    """注册内置分析工具"""
    from analysis.quantitative import (
        basic_stats, sentiment_analysis, word_frequency, time_series
    )
    from analysis.qualitative import (
        theme_extraction, content_category, insight_mining
    )

    # 基础统计
    ToolsRegistry.register(AnalysisTool(
        name="basic_stats",
        category=AnalysisCategory.QUANTITATIVE,
        description="基础统计分析：计数、均值、中位数、最值、分布",
        function=basic_stats,
        required_fields=[],  # 适用于任何数据
        output_type="stats",
        priority=10,
        examples=["统计分析", "描述性统计", "数据概览"]
    ))

    # 情感分析
    ToolsRegistry.register(AnalysisTool(
        name="sentiment_analysis",
        category=AnalysisCategory.TEXT_ANALYSIS,
        description="情感分析：使用 SnowNLP 分析文本情感倾向（正面/中性/负面）",
        function=sentiment_analysis,
        required_fields=["text"],
        output_type="sentiment",
        priority=9,
        examples=["情感分析", "正负面判断", "用户满意度"]
    ))

    # 词频统计
    ToolsRegistry.register(AnalysisTool(
        name="word_frequency",
        category=AnalysisCategory.TEXT_ANALYSIS,
        description="词频统计：使用 jieba 分词，提取 TF-IDF 关键词和高频词汇",
        function=word_frequency,
        required_fields=["text"],
        output_type="keywords",
        priority=8,
        examples=["词频统计", "关键词提取", "TF-IDF 分析"]
    ))

    # 时间序列
    ToolsRegistry.register(AnalysisTool(
        name="time_series",
        category=AnalysisCategory.TIME_SERIES,
        description="时间序列分析：按时间聚合，分析趋势和周期性",
        function=time_series,
        required_fields=["date"],
        output_type="time_data",
        priority=7,
        examples=["时间趋势", "周期性分析", "按日/周/月统计"]
    ))

    # 主题提取
    ToolsRegistry.register(AnalysisTool(
        name="theme_extraction",
        category=AnalysisCategory.QUALITATIVE,
        description="主题提取：使用 LLM 从文本中提取核心主题",
        function=theme_extraction,
        required_fields=["text"],
        output_type="themes",
        priority=6,
        examples=["主题提取", "内容分类", "核心话题"]
    ))

    # 内容分类
    ToolsRegistry.register(AnalysisTool(
        name="content_category",
        category=AnalysisCategory.QUALITATIVE,
        description="内容分类：使用 LLM 将内容自动归类",
        function=content_category,
        required_fields=["text"],
        output_type="categories",
        priority=5,
        examples=["内容分类", "自动归类", "分类统计"]
    ))

    # 观点挖掘
    ToolsRegistry.register(AnalysisTool(
        name="insight_mining",
        category=AnalysisCategory.QUALITATIVE,
        description="观点挖掘：提取用户态度、问题、建议、需求",
        function=insight_mining,
        required_fields=["text"],
        output_type="insights",
        priority=4,
        examples=["观点挖掘", "用户反馈", "需求分析"]
    ))

    # ========== 高级分析工具 ==========

    from analysis.advanced import comment_clustering, user_activity, interaction_network

    # 评论聚类
    ToolsRegistry.register(AnalysisTool(
        name="comment_clustering",
        category=AnalysisCategory.ADVANCED,
        description="评论聚类：基于关键词重叠将相似评论自动分组，识别重复讨论和热点话题",
        function=comment_clustering,
        required_fields=["text"],
        output_type="clusters",
        priority=3,
        examples=["评论聚类", "相似评论分组", "重复讨论识别"]
    ))

    # 用户活跃度
    ToolsRegistry.register(AnalysisTool(
        name="user_activity",
        category=AnalysisCategory.ADVANCED,
        description="用户活跃度：分析谁评论最多、互动最高、内容最长",
        function=user_activity,
        required_fields=[],  # 自动检测用户字段
        output_type="user_stats",
        priority=3,
        examples=["用户活跃度", "评论排行", "互动排行"]
    ))

    # 互动网络
    ToolsRegistry.register(AnalysisTool(
        name="interaction_network",
        category=AnalysisCategory.ADVANCED,
        description="互动网络：分析评论中的回复关系，识别互动密集用户和孤立用户",
        function=interaction_network,
        required_fields=[],  # 自动检测回复关系
        output_type="network",
        priority=2,
        examples=["互动网络", "回复关系", "社交网络"]
    ))

    logger.info(f"已注册 {len(ToolsRegistry.get_all_tools())} 个内置分析工具")


# 初始化时注册工具
_register_builtin_tools()


# ==================== 便捷函数 ====================

def get_available_tools() -> List[Dict[str, Any]]:
    """获取可用工具列表"""
    tools = ToolsRegistry.get_all_tools()
    return [
        {
            "name": t.name,
            "category": t.category.value,
            "description": t.description,
            "required_fields": t.required_fields,
            "examples": t.examples,
        }
        for t in tools
    ]


def recommend_tools(data: List[Dict]) -> List[str]:
    """根据数据推荐工具"""
    tools = ToolsRegistry.get_tools_for_data(data)
    return [t.name for t in tools]


def execute_tool(tool_name: str, data: List[Dict], data_file: Path) -> Dict[str, Any]:
    """执行指定工具"""
    tool = ToolsRegistry.get_tool(tool_name)
    if not tool:
        return {"error": f"未知工具: {tool_name}"}

    try:
        # 根据工具类型调用不同的函数签名
        # 有些工具需要 text_field 参数，有些需要 data_file
        if tool_name in ["sentiment_analysis", "word_frequency", "theme_extraction",
                         "content_category", "insight_mining",
                         "comment_clustering"]:
            # 这些工具第二个参数是 text_field（可选）
            result = tool.function(data, None)
        elif tool_name in ["user_activity", "interaction_network"]:
            # 这些工具只需要 data，其他参数自动检测
            result = tool.function(data)
        elif tool_name in ["basic_stats"]:
            # 这些工具第二个参数是 file_path
            result = tool.function(data, data_file)
        else:
            # 默认调用方式
            result = tool.function(data, data_file)
        return result
    except Exception as e:
        logger.error(f"工具执行失败 [{tool_name}]: {e}")
        return {"error": f"执行失败: {e}"}


def get_tools_description_for_ai() -> str:
    """获取工具描述（供 AI 使用）"""
    return ToolsRegistry.generate_tools_description()
