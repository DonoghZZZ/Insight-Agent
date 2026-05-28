"""分析工具系统测试"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.tools_registry import (
    ToolsRegistry, AnalysisCategory, AnalysisTool,
    execute_tool, recommend_tools, get_available_tools
)
from analysis.smart_analyzer import smart_analyze


@pytest.fixture
def sample_data():
    """示例数据"""
    return [
        {"content": "这个产品非常好用", "score": "85", "date": "2024-01-15"},
        {"content": "体验很差，不推荐", "score": "45", "date": "2024-01-16"},
        {"content": "一般般，没什么感觉", "score": "65", "date": "2024-01-17"},
        {"content": "强烈推荐，物超所值", "score": "95", "date": "2024-01-18"},
        {"content": "还需要改进", "score": "55", "date": "2024-01-19"},
    ]


@pytest.fixture
def data_file():
    """数据文件路径"""
    return Path("test_data.csv")


class TestToolsRegistry:
    """工具注册表测试"""

    def test_get_all_tools(self):
        """测试获取所有工具"""
        tools = get_available_tools()
        assert len(tools) > 0
        assert all(isinstance(t, dict) for t in tools)

    def test_get_tool(self):
        """测试获取单个工具"""
        tool = ToolsRegistry.get_tool("sentiment_analysis")
        assert tool is not None
        assert tool.name == "sentiment_analysis"
        assert tool.category == AnalysisCategory.TEXT_ANALYSIS

    def test_search_tools(self):
        """测试搜索工具"""
        tools = ToolsRegistry.search_tools("情感")
        assert len(tools) > 0
        assert any("情感" in t.description for t in tools)

    def test_get_tools_by_category(self):
        """测试按类别获取工具"""
        text_tools = ToolsRegistry.get_tools_by_category(AnalysisCategory.TEXT_ANALYSIS)
        assert len(text_tools) > 0
        assert all(t.category == AnalysisCategory.TEXT_ANALYSIS for t in text_tools)


class TestToolExecution:
    """工具执行测试"""

    def test_sentiment_analysis(self, sample_data, data_file):
        """测试情感分析"""
        result = execute_tool("sentiment_analysis", sample_data, data_file)
        assert "error" not in result
        assert "total" in result
        assert "positive" in result
        assert "negative" in result

    def test_basic_stats(self, sample_data, data_file):
        """测试基础统计"""
        result = execute_tool("basic_stats", sample_data, data_file)
        assert "error" not in result
        assert "record_count" in result
        assert result["record_count"] == len(sample_data)

    def test_word_frequency(self, sample_data, data_file):
        """测试词频统计"""
        result = execute_tool("word_frequency", sample_data, data_file)
        assert "error" not in result
        assert "keywords" in result

    def test_unknown_tool(self, sample_data, data_file):
        """测试未知工具"""
        result = execute_tool("unknown_tool", sample_data, data_file)
        assert "error" in result


class TestToolRecommendation:
    """工具推荐测试"""

    def test_recommend_tools(self, sample_data):
        """测试工具推荐"""
        recommended = recommend_tools(sample_data)
        assert len(recommended) > 0
        assert "sentiment_analysis" in recommended

    def test_recommend_with_text_data(self):
        """测试纯文本数据推荐"""
        data = [{"content": "测试文本"}]
        recommended = recommend_tools(data)
        assert "sentiment_analysis" in recommended

    def test_recommend_with_numeric_data(self):
        """测试纯数值数据推荐"""
        data = [{"score": "85"}, {"score": "92"}]
        recommended = recommend_tools(data)
        assert "basic_stats" in recommended


class TestSmartAnalyzer:
    """智能分析测试"""

    def test_analyze_with_matching_tool(self, sample_data, data_file):
        """测试匹配工具的分析"""
        result = smart_analyze(sample_data, data_file, "帮我做情感分析")
        assert result.success
        assert result.source == "builtin"
        assert result.tool_name == "sentiment_analysis"

    def test_analyze_with_keyword_match(self, sample_data, data_file):
        """测试关键词匹配"""
        result = smart_analyze(sample_data, data_file, "统计一下数据")
        assert result.success
        assert result.source == "builtin"
        assert result.tool_name == "basic_stats"

    def test_analyze_with_no_match(self, sample_data, data_file):
        """测试无匹配（应调用大模型）"""
        # 注意：这个测试需要 API key，可能失败
        # result = smart_analyze(sample_data, data_file, "分析潜在需求")
        # assert result.source == "llm"
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
