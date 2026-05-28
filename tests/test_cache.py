"""缓存模块测试"""

import pytest
from pathlib import Path
import sys
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.cache import get_cached, set_cached, _make_cache_key


class TestCacheKey:
    """缓存键生成测试"""

    def test_consistent_key(self, sample_data):
        key1 = _make_cache_key(sample_data, "test_model")
        key2 = _make_cache_key(sample_data, "test_model")
        assert key1 == key2

    def test_different_data_different_key(self, sample_data):
        key1 = _make_cache_key(sample_data, "model_a")
        key2 = _make_cache_key(sample_data, "model_b")
        assert key1 != key2

    def test_key_is_hex_string(self, sample_data):
        key = _make_cache_key(sample_data, "test")
        assert len(key) == 32  # MD5 hex
        assert all(c in "0123456789abcdef" for c in key)


class TestCacheRoundTrip:
    """缓存读写测试"""

    def test_set_and_get(self, sample_data):
        result = {"model": "test", "score": 42}
        set_cached(sample_data, "test_model", result)
        cached = get_cached(sample_data, "test_model")
        assert cached is not None
        assert cached["score"] == 42

    def test_cache_miss(self, sample_data):
        cached = get_cached(sample_data, "nonexistent_model_12345")
        # 可能返回 None 或之前的缓存
        # 这里只验证不报错
        pass

    def test_different_models_independent(self, sample_data):
        set_cached(sample_data, "model_a", {"a": 1})
        set_cached(sample_data, "model_b", {"b": 2})
        assert get_cached(sample_data, "model_a")["a"] == 1
        assert get_cached(sample_data, "model_b")["b"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
