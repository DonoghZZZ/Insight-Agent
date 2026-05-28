"""分析模块测试"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.quantitative import (
    auto_detect_fields,
    basic_stats,
    sentiment_analysis,
    word_frequency,
)


class TestAutoDetectFields:
    """字段自动检测测试"""

    def test_detect_text_field(self):
        """测试文本字段检测"""
        data = [
            {"content": "这是一段文本", "score": "85"},
            {"content": "另一段文本", "score": "92"},
        ]
        fields = auto_detect_fields(data)
        assert "content" in fields
        assert fields["content"] == "text"

    def test_detect_numeric_field(self):
        """测试数值字段检测"""
        data = [
            {"name": "test", "score": "85"},
            {"name": "test2", "score": "92"},
        ]
        fields = auto_detect_fields(data)
        assert "score" in fields
        assert fields["score"] == "numeric"

    def test_detect_date_field(self):
        """测试日期字段检测"""
        data = [
            {"content": "test", "date": "2024-01-15"},
            {"content": "test2", "date": "2024-01-16"},
        ]
        fields = auto_detect_fields(data)
        assert "date" in fields
        assert fields["date"] == "date"

    def test_with_empty_data(self):
        """测试空数据"""
        fields = auto_detect_fields([])
        assert fields == {}

    def test_with_single_row(self):
        """测试单行数据"""
        data = [{"name": "test", "value": "123"}]
        fields = auto_detect_fields(data)
        assert "name" in fields
        assert "value" in fields


class TestBasicStats:
    """基础统计测试"""

    def test_basic_stats_with_numeric_data(self):
        """测试数值统计"""
        data = [
            {"score": "85"},
            {"score": "92"},
            {"score": "78"},
        ]
        result = basic_stats(data, Path("test.csv"))
        assert "record_count" in result
        assert result["record_count"] == 3
        assert "fields" in result

    def test_basic_stats_with_text_data(self):
        """测试文本统计"""
        data = [
            {"content": "这是一段文本"},
            {"content": "另一段文本"},
        ]
        result = basic_stats(data, Path("test.csv"))
        assert "record_count" in result
        assert result["record_count"] == 2

    def test_basic_stats_with_empty_data(self):
        """测试空数据"""
        result = basic_stats([], Path("test.csv"))
        assert "record_count" in result
        assert result["record_count"] == 0


class TestSentimentAnalysis:
    """情感分析测试"""

    def test_sentiment_with_positive_text(self):
        """测试正面情感"""
        data = [
            {"content": "这个产品非常好，我很喜欢"},
            {"content": "太棒了，强烈推荐"},
        ]
        result = sentiment_analysis(data, Path("test.csv"))
        assert "total" in result
        assert "positive" in result

    def test_sentiment_with_negative_text(self):
        """测试负面情感"""
        data = [
            {"content": "这个产品太差了，很失望"},
            {"content": "不好用，不推荐"},
        ]
        result = sentiment_analysis(data, Path("test.csv"))
        assert "total" in result
        assert "negative" in result

    def test_sentiment_with_empty_data(self):
        """测试空数据"""
        result = sentiment_analysis([], Path("test.csv"))
        assert "total" in result
        assert result["total"] == 0


class TestWordFrequency:
    """词频统计测试"""

    def test_word_frequency_with_chinese_text(self):
        """测试中文词频"""
        data = [
            {"content": "人工智能是未来的发展方向"},
            {"content": "机器学习是人工智能的重要分支"},
        ]
        result = word_frequency(data, Path("test.csv"))
        assert "top_words" in result
        assert "keywords" in result

    def test_word_frequency_with_empty_data(self):
        """测试空数据"""
        result = word_frequency([], Path("test.csv"))
        assert "top_words" in result
        assert result["top_words"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
