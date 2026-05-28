# 知网爬虫配置模块

import random
from typing import List, Dict, Any

class Settings:
    """爬虫全局配置"""
    
    # 知网基础URL
    BASE_URL = "https://kns.cnki.net"
    SEARCH_URL = "https://kns.cnki.net/kns8s/defaultresult/index"
    
    # 请求头配置 - User-Agent轮换池
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    # 请求配置
    REQUEST_TIMEOUT = 30  # 请求超时时间(秒)
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 2  # 重试间隔(秒)
    MIN_DELAY = 1.5  # 最小请求间隔(秒)
    MAX_DELAY = 4.0  # 最大请求间隔(秒)
    
    # 代理配置(可选)
    PROXY_ENABLED = False
    PROXY_LIST: List[str] = []
    
    # 数据导出配置
    EXPORT_FORMATS = ["csv", "json", "xlsx"]
    DEFAULT_EXPORT_FORMAT = "csv"
    
    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        """获取随机User-Agent"""
        return random.choice(cls.USER_AGENTS)
    
    @classmethod
    def get_random_delay(cls) -> float:
        """获取随机延迟时间"""
        return random.uniform(cls.MIN_DELAY, cls.MAX_DELAY)
    
    @classmethod
    def get_proxy(cls) -> Dict[str, str]:
        """获取代理配置"""
        if cls.PROXY_ENABLED and cls.PROXY_LIST:
            proxy = random.choice(cls.PROXY_LIST)
            return {
                "http": f"http://{proxy}",
                "https": f"https://{proxy}"
            }
        return {}
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """转换为字典"""
        return {k: v for k, v in cls.__dict__.items() 
                if not k.startswith('_') and not callable(v)}


# 搜索配置
class SearchConfig:
    """搜索功能配置"""
    
    # 搜索模式
    SEARCH_MODES = {
        "default": "kns8s/defaultresult/index",  # 默认搜索
        "advanced": "kns8s/advanced/search",    # 高级搜索
        "author": "kns8s/author",               # 作者搜索
    }
    
    # 可搜索的文献类型
    LITERATURE_TYPES = {
        "journal": "期刊",      # 学术期刊
        "thesis": "学位论文",   # 硕博士论文
        "conference": "会议",   # 学术会议
        "newspaper": "报纸",    # 报纸文章
        "yearbook": "年鉴",     # 年鉴
        "patent": "专利",       # 专利
        "standard": "标准",     # 标准
    }
    
    # 排序方式
    SORT_OPTIONS = {
        "relevance": "相关度",
        "date": "发表时间",
        "cite": "被引次数",
        "download": "下载次数",
    }
    
    # 每页结果数
    PAGE_SIZE = 20
    
    # 最大搜索页数
    MAX_PAGES = 50


# 存储配置
class StorageConfig:
    """数据存储配置"""
    
    # 默认存储路径
    DEFAULT_DATA_DIR = "./data"
    DEFAULT_OUTPUT_DIR = "./output"
    
    # CSV配置
    CSV_ENCODING = "utf-8-sig"  # UTF-8 with BOM，确保Excel兼容
    
    # JSON配置
    JSON_INDENT = 2
    JSON_ENSURE_ASCII = False
    
    # Excel配置
    EXCEL_ENGINE = "openpyxl"
    EXCEL_SHEET_NAME = "论文数据"


settings = Settings()
search_config = SearchConfig()
storage_config = StorageConfig()
