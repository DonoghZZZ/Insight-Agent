#!/usr/bin/env python3
"""性能监控和优化模块"""

import time
import functools
import logging
from typing import Callable, Any
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""

    _metrics = {}

    @classmethod
    def record(cls, name: str, duration: float, success: bool = True):
        """记录性能指标"""
        if name not in cls._metrics:
            cls._metrics[name] = {
                "count": 0,
                "total_time": 0,
                "success_count": 0,
                "fail_count": 0,
                "min_time": float("inf"),
                "max_time": 0,
                "last_time": None,
            }

        metric = cls._metrics[name]
        metric["count"] += 1
        metric["total_time"] += duration
        metric["min_time"] = min(metric["min_time"], duration)
        metric["max_time"] = max(metric["max_time"], duration)
        metric["last_time"] = datetime.now().isoformat()

        if success:
            metric["success_count"] += 1
        else:
            metric["fail_count"] += 1

    @classmethod
    def get_stats(cls, name: str) -> dict:
        """获取统计信息"""
        if name not in cls._metrics:
            return {}

        metric = cls._metrics[name]
        return {
            "name": name,
            "count": metric["count"],
            "total_time": metric["total_time"],
            "avg_time": metric["total_time"] / metric["count"] if metric["count"] > 0 else 0,
            "min_time": metric["min_time"] if metric["min_time"] != float("inf") else 0,
            "max_time": metric["max_time"],
            "success_rate": metric["success_count"] / metric["count"] * 100 if metric["count"] > 0 else 0,
            "last_time": metric["last_time"],
        }

    @classmethod
    def get_all_stats(cls) -> dict:
        """获取所有统计信息"""
        return {name: cls.get_stats(name) for name in cls._metrics}

    @classmethod
    def reset(cls):
        """重置统计"""
        cls._metrics.clear()


def timer(func: Callable) -> Callable:
    """计时装饰器"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        success = True
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise
        finally:
            duration = time.time() - start
            PerformanceMonitor.record(func.__name__, duration, success)
            logger.debug(f"{func.__name__} 执行时间: {duration:.3f}秒")

    return wrapper


@contextmanager
def measure_time(name: str):
    """计时上下文管理器"""
    start = time.time()
    success = True
    try:
        yield
    except Exception as e:
        success = False
        raise
    finally:
        duration = time.time() - start
        PerformanceMonitor.record(name, duration, success)
        logger.debug(f"{name} 执行时间: {duration:.3f}秒")


class MemoryOptimizer:
    """内存优化器"""

    @staticmethod
    def get_memory_usage() -> dict:
        """获取内存使用情况"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss": memory_info.rss / 1024 / 1024,  # MB
                "vms": memory_info.vms / 1024 / 1024,  # MB
                "percent": process.memory_percent(),
            }
        except ImportError:
            return {"error": "psutil 未安装"}

    @staticmethod
    def optimize_dataframe(df):
        """优化 DataFrame 内存使用"""
        try:
            import pandas as pd

            # 优化数值列
            for col in df.select_dtypes(include=["int64"]).columns:
                if df[col].min() >= 0:
                    if df[col].max() < 255:
                        df[col] = df[col].astype("uint8")
                    elif df[col].max() < 65535:
                        df[col] = df[col].astype("uint16")
                    elif df[col].max() < 4294967295:
                        df[col] = df[col].astype("uint32")
                else:
                    if df[col].min() > -128 and df[col].max() < 127:
                        df[col] = df[col].astype("int8")
                    elif df[col].min() > -32768 and df[col].max() < 32767:
                        df[col] = df[col].astype("int16")

            # 优化浮点列
            for col in df.select_dtypes(include=["float64"]).columns:
                df[col] = pd.to_numeric(df[col], downcast="float")

            # 优化对象列
            for col in df.select_dtypes(include=["object"]).columns:
                if df[col].nunique() / len(df) < 0.5:  # 唯一值少于50%
                    df[col] = df[col].astype("category")

            return df
        except Exception as e:
            logger.warning(f"DataFrame 优化失败: {e}")
            return df


class CacheManager:
    """缓存管理器"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl

    def get(self, key: str) -> Any:
        """获取缓存"""
        if key in self.cache:
            item = self.cache[key]
            if time.time() - item["timestamp"] < self.ttl:
                return item["value"]
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """设置缓存"""
        # 清理过期缓存
        self._cleanup()

        # 如果缓存已满，删除最旧的
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]

        self.cache[key] = {
            "value": value,
            "timestamp": time.time(),
        }

    def _cleanup(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self.cache.items()
            if current_time - item["timestamp"] >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

    def clear(self):
        """清空缓存"""
        self.cache.clear()

    def stats(self) -> dict:
        """缓存统计"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
        }


# 全局缓存实例
cache = CacheManager()


def cached(ttl: int = 3600):
    """缓存装饰器"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # 尝试从缓存获取
            result = cache.get(key)
            if result is not None:
                logger.debug(f"缓存命中: {func.__name__}")
                return result

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache.set(key, result)
            logger.debug(f"缓存存储: {func.__name__}")

            return result

        return wrapper

    return decorator


def print_performance_report():
    """打印性能报告"""
    stats = PerformanceMonitor.get_all_stats()

    if not stats:
        print("暂无性能数据")
        return

    print("\n" + "=" * 60)
    print("📊 性能报告")
    print("=" * 60)

    for name, stat in stats.items():
        print(f"\n{name}:")
        print(f"  调用次数: {stat['count']}")
        print(f"  平均耗时: {stat['avg_time']:.3f}秒")
        print(f"  最小耗时: {stat['min_time']:.3f}秒")
        print(f"  最大耗时: {stat['max_time']:.3f}秒")
        print(f"  成功率: {stat['success_rate']:.1f}%")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 测试性能监控
    @timer
    def test_function():
        time.sleep(0.1)
        return "done"

    test_function()
    test_function()
    print_performance_report()
