"""工具注册表测试"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.tools_registry import (
    ToolsRegistry, get_available_tools, recommend_tools,
    execute_tool, AnalysisCategory,
)


class TestToolsRegistry:
    """工具注册表测试"""

    def test_all_tools_registered(self):
        tools = ToolsRegistry.get_all_tools()
        assert len(tools) >= 10

    def test_get_tool_by_name(self):
        tool = ToolsRegistry.get_tool("basic_stats")
        assert tool is not None
        assert tool.name == "basic_stats"

    def test_get_nonexistent_tool(self):
        tool = ToolsRegistry.get_tool("nonexistent")
        assert tool is None

    def test_tools_by_category(self):
        quant_tools = ToolsRegistry.get_tools_by_category(AnalysisCategory.QUANTITATIVE)
        assert len(quant_tools) >= 3
        qual_tools = ToolsRegistry.get_tools_by_category(AnalysisCategory.QUALITATIVE)
        assert len(qual_tools) >= 3

    def test_search_tools(self):
        results = ToolsRegistry.search_tools("情感")
        assert len(results) >= 1

    def test_tools_for_data(self, sample_data):
        recommended = ToolsRegistry.get_tools_for_data(sample_data)
        assert len(recommended) > 0


class TestGetAvailableTools:
    """可用工具列表测试"""

    def test_returns_list(self):
        tools = get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 10

    def test_tool_has_required_fields(self):
        tools = get_available_tools()
        for tool in tools:
            assert "name" in tool
            assert "category" in tool
            assert "description" in tool


class TestRecommendTools:
    """工具推荐测试"""

    def test_recommend_for_text_data(self, sample_text_data):
        recommended = recommend_tools(sample_text_data)
        assert "word_frequency" in recommended or "sentiment_analysis" in recommended

    def test_recommend_for_empty_data(self):
        recommended = recommend_tools([])
        assert recommended == []


class TestExecuteTool:
    """工具执行测试"""

    def test_execute_basic_stats(self, sample_data):
        result = execute_tool("basic_stats", sample_data, Path("test.csv"))
        assert "error" not in result or "record_count" in result

    def test_execute_sentiment(self, sample_text_data):
        result = execute_tool("sentiment_analysis", sample_text_data, Path("test.csv"))
        assert "error" not in result or "total" in result

    def test_execute_word_frequency(self, sample_text_data):
        result = execute_tool("word_frequency", sample_text_data, Path("test.csv"))
        assert "error" not in result or "top_words" in result

    def test_execute_nonexistent_tool(self, sample_data):
        result = execute_tool("nonexistent_tool", sample_data, Path("test.csv"))
        assert "error" in result

    def test_execute_user_activity(self):
        data = [
            {"昵称": "user1", "content": "hello"},
            {"昵称": "user2", "content": "world"},
        ]
        result = execute_tool("user_activity", data, Path("test.csv"))
        assert "total_users" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
