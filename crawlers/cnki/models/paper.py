"""
论文/文献数据模型
定义论文信息的数据结构和操作方法
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


@dataclass
class Paper:
    """
    论文数据模型
    包含论文的基本信息和元数据
    """
    # 基本信息
    title: str = ""                    # 论文标题
    authors: List[str] = field(default_factory=list)  # 作者列表
    author_affiliations: List[str] = field(default_factory=list)  # 作者单位
    
    # 出版信息
    source: str = ""                   # 来源期刊/会议
    publish_date: str = ""              # 发表日期
    volume: str = ""                    # 卷号
    issue: str = ""                     # 期号
    pages: str = ""                     # 页码
    
    # 分类信息
    doi: str = ""                        # DOI编号
    issn: str = ""                       # ISSN
    cn_number: str = ""                  # CN号(中国知网特有)
    
    # 学术指标
    abstract: str = ""                   # 摘要
    keywords: List[str] = field(default_factory=list)  # 关键词
    subject: str = ""                    # 学科分类
    
    # 统计数据
    cited_count: int = 0                # 被引次数
    download_count: int = 0              # 下载次数
    
    # 链接信息
    url: str = ""                        # 知网链接
    pdf_url: str = ""                    # PDF下载链接
    
    # 元数据
    crawl_time: str = ""                 # 爬取时间
    source_type: str = ""                # 文献类型(期刊/学位论文等)
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.crawl_time:
            self.crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Paper":
        """从字典创建Paper对象"""
        return cls(**data)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Paper(title='{self.title[:30]}...', authors={self.authors}, source='{self.source}')"
    
    def __repr__(self) -> str:
        """调试表示"""
        return self.__str__()
    
    def is_valid(self) -> bool:
        """检查数据是否有效"""
        return bool(self.title and self.source)
    
    @property
    def display_authors(self) -> str:
        """获取格式化的作者字符串"""
        return "、".join(self.authors) if self.authors else ""
    
    @property
    def display_keywords(self) -> str:
        """获取格式化的关键词字符串"""
        return "；".join(self.keywords) if self.keywords else ""


@dataclass
class SearchResult:
    """
    搜索结果数据模型
    包含搜索统计信息和论文列表
    """
    query: str = ""                      # 搜索关键词
    total_count: int = 0                # 总结果数
    papers: List[Paper] = field(default_factory=list)  # 论文列表
    search_time: str = ""               # 搜索时间
    page: int = 1                        # 当前页码
    page_size: int = 20                  # 每页数量
    
    def __post_init__(self):
        if not self.search_time:
            self.search_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def add_paper(self, paper: Paper):
        """添加论文到结果集"""
        self.papers.append(paper)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "total_count": self.total_count,
            "papers": [p.to_dict() for p in self.papers],
            "search_time": self.search_time,
            "page": self.page,
            "page_size": self.page_size
        }
    
    @property
    def total_pages(self) -> int:
        """计算总页数"""
        if self.page_size <= 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size
    
    def __len__(self) -> int:
        """返回论文数量"""
        return len(self.papers)
