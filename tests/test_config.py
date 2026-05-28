"""配置验证测试"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from validator import ConfigValidator, DataValidator


class TestConfigValidator:
    """配置验证器测试"""

    def test_validate_returns_tuple(self):
        """测试返回类型"""
        result = ConfigValidator.validate()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_validate_returns_bool_and_list(self):
        """测试返回值类型"""
        is_valid, errors = ConfigValidator.validate()
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_print_status_returns_bool(self):
        """测试 print_status 返回值"""
        result = ConfigValidator.print_status()
        assert isinstance(result, bool)


class TestDataValidator:
    """数据验证器测试"""

    def test_validate_data_with_valid_data(self):
        """测试有效数据验证"""
        data = [{"name": "test", "value": "123"}]
        is_valid, message = DataValidator.validate_data(data)
        assert is_valid is True
        assert "通过" in message

    def test_validate_data_with_none(self):
        """测试空数据"""
        is_valid, message = DataValidator.validate_data(None)
        assert is_valid is False
        assert "为空" in message

    def test_validate_data_with_empty_list(self):
        """测试空列表"""
        is_valid, message = DataValidator.validate_data([])
        assert is_valid is False
        assert "为空" in message

    def test_validate_data_with_invalid_type(self):
        """测试无效类型"""
        is_valid, message = DataValidator.validate_data("not a list")
        assert is_valid is False
        assert "列表" in message

    def test_validate_data_with_invalid_element(self):
        """测试无效元素"""
        is_valid, message = DataValidator.validate_data([1, 2, 3])
        assert is_valid is False
        assert "字典" in message

    def test_validate_file_with_valid_file(self, tmp_path):
        """测试有效文件"""
        test_file = tmp_path / "test.csv"
        test_file.write_text("name,value\ntest,123")
        is_valid, message = DataValidator.validate_file(test_file)
        assert is_valid is True
        assert "通过" in message

    def test_validate_file_with_nonexistent(self):
        """测试不存在的文件"""
        is_valid, message = DataValidator.validate_file(Path("/nonexistent/file.csv"))
        assert is_valid is False
        assert "不存在" in message

    def test_validate_file_with_invalid_extension(self, tmp_path):
        """测试无效扩展名"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        is_valid, message = DataValidator.validate_file(test_file)
        assert is_valid is False
        assert "格式" in message

    def test_validate_crawler_params_zhihu(self):
        """测试知乎爬虫参数验证"""
        # 有效参数
        is_valid, _ = DataValidator.validate_crawler_params("知乎", {"url": "https://zhihu.com/xxx"})
        assert is_valid is True

        # 无效参数
        is_valid, _ = DataValidator.validate_crawler_params("知乎", {})
        assert is_valid is False

    def test_validate_crawler_params_cnki(self):
        """测试知网爬虫参数验证"""
        # 有效参数
        is_valid, _ = DataValidator.validate_crawler_params("中国知网", {"keyword": "人工智能"})
        assert is_valid is True

        # 无效参数
        is_valid, _ = DataValidator.validate_crawler_params("中国知网", {})
        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
