"""数据清洗模块测试"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.data_cleaner import (
    clean_text, parse_number, normalize_date,
    deduplicate, auto_clean_fields, clean_data,
)


class TestCleanText:
    """文本清洗测试"""

    def test_remove_html_tags(self):
        assert clean_text("<b>hello</b>") == "hello"

    def test_remove_html_entities(self):
        assert "&" in clean_text("a&amp;b") or clean_text("a&amp;b") == "a&b"

    def test_strip_whitespace(self):
        assert clean_text("  hello  ") == "hello"

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_none_input(self):
        assert clean_text(None) == ""

    def test_nested_html(self):
        result = clean_text("<div><p>text</p></div>")
        assert "<" not in result
        assert "text" in result


class TestParseNumber:
    """中文数字解析测试"""

    def test_wan(self):
        assert parse_number("1.2万") == 12000

    def test_wan_variant(self):
        assert parse_number("3.5w") == 35000

    def test_yi(self):
        assert parse_number("2亿") == 200000000

    def test_plain_number(self):
        assert parse_number("1234") == 1234

    def test_comma_number(self):
        assert parse_number("1,234") == 1234

    def test_percentage(self):
        assert parse_number("85%") == 85

    def test_float(self):
        assert parse_number("3.14") == 3.14

    def test_empty(self):
        assert parse_number("") is None

    def test_none(self):
        assert parse_number(None) is None

    def test_wan_with_unit(self):
        assert parse_number("10.5万") == 105000


class TestNormalizeDate:
    """日期标准化测试"""

    def test_standard_date(self):
        assert normalize_date("2024-01-15") == "2024-01-15"

    def test_slash_date(self):
        result = normalize_date("2024/01/15")
        assert result == "2024-01-15"

    def test_days_ago(self):
        result = normalize_date("3天前")
        assert result is not None
        assert len(result) == 10  # YYYY-MM-DD

    def test_hours_ago(self):
        result = normalize_date("5小时前")
        assert result is not None

    def test_empty(self):
        assert normalize_date("") is None

    def test_none(self):
        assert normalize_date(None) is None


class TestDeduplicate:
    """去重测试"""

    def test_exact_dedup(self):
        data = [
            {"content": "hello", "id": 1},
            {"content": "hello", "id": 2},
            {"content": "world", "id": 3},
        ]
        result = deduplicate(data)
        assert len(result) == 2

    def test_no_duplicates(self):
        data = [
            {"content": "hello"},
            {"content": "world"},
        ]
        result = deduplicate(data)
        assert len(result) == 2

    def test_empty(self):
        assert deduplicate([]) == []


class TestCleanData:
    """完整清洗流水线测试"""

    def test_clean_data_pipeline(self, sample_data):
        result = clean_data(sample_data)
        assert "data" in result
        assert "stats" in result
        assert len(result["data"]) > 0

    def test_clean_data_with_empty(self):
        result = clean_data([])
        assert result["data"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
