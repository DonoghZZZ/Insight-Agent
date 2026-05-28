"""测试配置和 fixtures"""

import pytest
from pathlib import Path
import sys
import tempfile
import shutil

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_data():
    """示例数据 fixture"""
    return [
        {"content": "这个产品非常好用", "score": "85", "date": "2024-01-15"},
        {"content": "体验很差，不推荐", "score": "45", "date": "2024-01-16"},
        {"content": "一般般，没什么感觉", "score": "65", "date": "2024-01-17"},
        {"content": "强烈推荐，物超所值", "score": "95", "date": "2024-01-18"},
        {"content": "还需要改进", "score": "55", "date": "2024-01-19"},
    ]


@pytest.fixture
def sample_text_data():
    """纯文本数据 fixture"""
    return [
        {"content": "人工智能是未来的发展方向"},
        {"content": "机器学习是人工智能的重要分支"},
        {"content": "深度学习在图像识别领域取得了突破"},
        {"content": "自然语言处理技术不断进步"},
        {"content": "AI 技术正在改变我们的生活"},
    ]


@pytest.fixture
def temp_dir():
    """临时目录 fixture"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # 清理
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_csv_file(temp_dir, sample_data):
    """示例 CSV 文件 fixture"""
    csv_file = temp_dir / "sample.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sample_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_data)
    return csv_file


@pytest.fixture
def sample_json_file(temp_dir, sample_data):
    """示例 JSON 文件 fixture"""
    import json

    json_file = temp_dir / "sample.json"
    json_file.write_text(json.dumps(sample_data, ensure_ascii=False), encoding="utf-8")
    return json_file


@pytest.fixture
def config_validator():
    """配置验证器 fixture"""
    from validator import ConfigValidator

    return ConfigValidator


@pytest.fixture
def data_validator():
    """数据验证器 fixture"""
    from validator import DataValidator

    return DataValidator
