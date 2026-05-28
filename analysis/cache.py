"""
分析结果缓存

避免对相同数据重复执行耗时分析（情感分析、词频统计等）
基于文件内容的 MD5 哈希 + 分析类型生成缓存 key
"""

import json
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# 缓存目录
from config import OUTPUT_DIR

CACHE_DIR = OUTPUT_DIR / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 缓存过期时间（秒）
DEFAULT_TTL = 3600 * 24  # 24 小时


def _file_hash(file_path: Path) -> str:
    """计算文件内容的 MD5 哈希"""
    h = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()[:12]


def _data_hash(data: list) -> str:
    """计算数据列表的哈希（基于前100条的 JSON）"""
    sample = json.dumps(data[:100], ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.md5(sample.encode()).hexdigest()[:12]


def _cache_key(file_path: Path, analysis_type: str, data: list = None) -> str:
    """生成缓存 key"""
    if file_path and file_path.exists():
        content_hash = _file_hash(file_path)
    elif data:
        content_hash = _data_hash(data)
    else:
        content_hash = "unknown"
    return f"{analysis_type}_{content_hash}"


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def get_cached(file_path: Path, analysis_type: str, data: list = None,
               ttl: int = DEFAULT_TTL) -> Optional[Dict[str, Any]]:
    """
    获取缓存的分析结果

    Returns:
        缓存的结果，或 None（未命中/已过期）
    """
    key = _cache_key(file_path, analysis_type, data)
    path = _cache_path(key)

    if not path.exists():
        return None

    try:
        cached = json.loads(path.read_text(encoding="utf-8"))

        # 检查过期
        cached_at = cached.get("_cached_at", 0)
        if time.time() - cached_at > ttl:
            path.unlink()  # 删除过期缓存
            logger.info(f"缓存已过期: {key}")
            return None

        logger.info(f"缓存命中: {key} ({analysis_type})")
        return cached.get("result")

    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.warning(f"读取缓存失败: {e}")
        return None


def set_cached(file_path: Path, analysis_type: str, result: Dict[str, Any],
               data: list = None):
    """保存分析结果到缓存"""
    key = _cache_key(file_path, analysis_type, data)
    path = _cache_path(key)

    try:
        cache_data = {
            "analysis_type": analysis_type,
            "result": result,
            "_cached_at": time.time(),
            "_cached_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        path.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2, default=str),
                        encoding="utf-8")
        logger.info(f"已缓存: {key} ({analysis_type})")
    except Exception as e:
        logger.warning(f"写入缓存失败: {e}")


def clear_cache(analysis_type: str = None):
    """清除缓存"""
    count = 0
    for f in CACHE_DIR.glob("*.json"):
        if analysis_type and not f.name.startswith(analysis_type):
            continue
        f.unlink()
        count += 1
    logger.info(f"已清除 {count} 个缓存文件")


def cached_analysis(analysis_type: str, ttl: int = DEFAULT_TTL):
    """
    分析函数的缓存装饰器

    用法：
        @cached_analysis("sentiment")
        def sentiment_analysis(data, text_field=None):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(data, *args, **kwargs):
            # 尝试用数据哈希做缓存 key
            data_hash = _data_hash(data)
            file_path = Path(f"inline_{data_hash}")

            # 检查缓存
            cached = get_cached(file_path, analysis_type, ttl=ttl)
            if cached is not None:
                cached["_from_cache"] = True
                return cached

            # 执行分析
            result = func(data, *args, **kwargs)

            # 缓存结果
            if result and "error" not in result:
                set_cached(file_path, analysis_type, result)

            return result
        return wrapper
    return decorator
