"""
工具函数模块
包含日志、文件操作、数据处理等辅助功能
"""

import os
import csv
import json
import time
import logging
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
    
    Returns:
        配置好的Logger对象
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def ensure_dir(path: str) -> Path:
    """
    确保目录存在，不存在则创建
    
    Args:
        path: 目录路径
    
    Returns:
        Path对象
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def generate_filename(prefix: str = "data", ext: str = "csv") -> str:
    """
    生成带时间戳的文件名
    
    Args:
        prefix: 文件名前缀
        ext: 文件扩展名
    
    Returns:
        格式化的文件名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{ext}"


def save_to_csv(data: List[Dict[str, Any]], filepath: str, encoding: str = "utf-8-sig") -> bool:
    """
    保存数据到CSV文件
    
    Args:
        data: 数据列表
        filepath: 文件路径
        encoding: 文件编码
    
    Returns:
        是否保存成功
    """
    if not data:
        return False
    
    try:
        ensure_dir(os.path.dirname(filepath))
        
        with open(filepath, 'w', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        return True
    except Exception as e:
        print(f"保存CSV失败: {e}")
        return False


def save_to_json(data: Any, filepath: str, indent: int = 2, ensure_ascii: bool = False) -> bool:
    """
    保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        filepath: 文件路径
        indent: 缩进空格数
        ensure_ascii: 是否转义非ASCII字符
    
    Returns:
        是否保存成功
    """
    try:
        ensure_dir(os.path.dirname(filepath))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent, default=str)
        
        return True
    except Exception as e:
        print(f"保存JSON失败: {e}")
        return False


def read_csv(filepath: str, encoding: str = "utf-8-sig") -> List[Dict[str, Any]]:
    """
    从CSV文件读取数据
    
    Args:
        filepath: 文件路径
        encoding: 文件编码
    
    Returns:
        数据列表
    """
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"读取CSV失败: {e}")
        return []


def calculate_hash(text: str) -> str:
    """
    计算文本的MD5哈希值
    
    Args:
        text: 输入文本
    
    Returns:
        MD5哈希字符串
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def rate_limit(delay: float):
    """
    简单的速率限制装饰器
    
    Args:
        delay: 延迟时间(秒)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            time.sleep(delay)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def clean_text(text: str) -> str:
    """
    清理文本，去除多余空白字符
    
    Args:
        text: 原始文本
    
    Returns:
        清理后的文本
    """
    if not text:
        return ""
    
    # 去除首尾空白
    text = text.strip()
    # 替换多个空白为单个空格
    text = ' '.join(text.split())
    return text


def parse_date_string(date_str: str) -> Optional[str]:
    """
    解析日期字符串，转换为标准格式
    
    Args:
        date_str: 日期字符串
    
    Returns:
        标准格式日期字符串或None
    """
    if not date_str:
        return None
    
    # 尝试多种日期格式
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y年%m月%d日",
        "%Y年%m月",
        "%Y-%m",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return date_str.strip()


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 字节数
    
    Returns:
        格式化的文件大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


class Timer:
    """简单的计时器上下文管理器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.time()
    
    @property
    def elapsed(self) -> float:
        """获取已用时间(秒)"""
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    def __str__(self) -> str:
        return f"{self.elapsed:.2f}秒"
