"""数据加载测试"""

import pytest
from pathlib import Path
import sys
import json
import csv

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataLoader:
    """数据加载器测试"""

    def test_load_csv(self, tmp_path):
        """测试加载 CSV 文件"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("name,value\ntest1,100\ntest2,200", encoding="utf-8")

        # 延迟导入，避免循环依赖
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from main import load_data

        data = load_data(csv_file)
        assert len(data) == 2
        assert data[0]["name"] == "test1"
        assert data[0]["value"] == "100"

    def test_load_json(self, tmp_path):
        """测试加载 JSON 文件"""
        json_file = tmp_path / "test.json"
        json_data = [{"name": "test1", "value": 100}, {"name": "test2", "value": 200}]
        json_file.write_text(json.dumps(json_data), encoding="utf-8")

        from main import load_data

        data = load_data(json_file)
        assert len(data) == 2
        assert data[0]["name"] == "test1"

    def test_load_json_dict_format(self, tmp_path):
        """测试加载字典格式的 JSON"""
        json_file = tmp_path / "test.json"
        json_data = {"data": [{"name": "test1"}, {"name": "test2"}]}
        json_file.write_text(json.dumps(json_data), encoding="utf-8")

        from main import load_data

        data = load_data(json_file)
        assert len(data) == 2

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        from main import load_data

        data = load_data(Path("/nonexistent/file.csv"))
        assert data == []

    def test_load_unsupported_format(self, tmp_path):
        """测试加载不支持的格式"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("test data")

        from main import load_data

        data = load_data(txt_file)
        assert data == []

    def test_load_empty_csv(self, tmp_path):
        """测试加载空 CSV"""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("name,value\n", encoding="utf-8")

        from main import load_data

        data = load_data(csv_file)
        # 空 CSV 只有表头，没有数据行
        assert len(data) == 0

    def test_load_csv_with_special_chars(self, tmp_path):
        """测试加载包含特殊字符的 CSV"""
        csv_file = tmp_path / "special.csv"
        csv_file.write_text(
            'name,description\ntest1,"这是一段,包含逗号的文本"\ntest2,"包含\n换行的文本"',
            encoding="utf-8",
        )

        from main import load_data

        data = load_data(csv_file)
        assert len(data) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
