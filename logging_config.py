"""统一日志配置

所有模块应通过 logging.getLogger(__name__) 获取 logger，
不要直接调用 logging.basicConfig()。
"""

import os
import logging
from pathlib import Path

_INITIALIZED = False


def setup_logging(level: str = None, log_file: str = None):
    """
    配置全局日志（只初始化一次）

    Args:
        level: 日志级别（默认从环境变量 LOG_LEVEL 读取，否则 INFO）
        log_file: 日志文件路径（默认 output/app.log）
    """
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True

    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")

    if log_file is None:
        log_file = str(Path(__file__).parent / "output" / "app.log")

    # 确保日志目录存在
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件 handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root_logger.addHandler(fh)

    # 控制台 handler（只显示 WARNING 及以上，避免干扰 Rich 输出）
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    # 抑制第三方库的 DEBUG 噪音
    for noisy in ("httpcore", "httpx", "openai", "urllib3", "playwright"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
