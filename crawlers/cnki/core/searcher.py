"""
知网搜索模块 - Selenium版本
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from config.settings import Settings, SearchConfig
from core.crawler import CNKIBrowser
from models.paper import Paper, SearchResult
from utils.helpers import setup_logger, Timer


class CNKISearcher:
    """
    知网搜索器
    使用Selenium实现搜索功能
    """
    
    def __init__(self, settings: Optional[Settings] = None, search_config: Optional[SearchConfig] = None):
        """
        初始化搜索器
        
        Args:
            settings: 爬虫配置
            search_config: 搜索配置
        """
        self.settings = settings or Settings()
        self.search_config = search_config or SearchConfig()
        self.logger = setup_logger(self.__class__.__name__)
        self._browser = None
        self._papers_cache: List[Paper] = []
    
    def _get_browser(self) -> CNKIBrowser:
        """获取或创建浏览器实例"""
        if self._browser is None:
            self._browser = CNKIBrowser(self.settings, headless=False)
        return self._browser
    
    def search(
        self,
        keyword: str,
        pages: int = 5,
        literature_type: Optional[str] = None,
        sort_by: str = "relevance"
    ) -> SearchResult:
        """
        搜索学术文献
        
        Args:
            keyword: 搜索关键词
            pages: 搜索页数
            literature_type: 文献类型
            sort_by: 排序方式
        
        Returns:
            SearchResult搜索结果对象
        """
        self.logger.info(f"开始搜索: {keyword}")
        
        with Timer() as timer:
            browser = self._get_browser()
            
            # 执行搜索
            raw_results = browser.search(
                keyword=keyword,
                pages=pages,
                literature_type=literature_type
            )
            
            # 转换为Paper对象
            papers = []
            for data in raw_results:
                paper = Paper(
                    title=data.get('title', ''),
                    authors=data.get('authors', '').split('、') if data.get('authors') else [],
                    source=data.get('source', ''),
                    publish_date=data.get('date', ''),
                    cited_count=int(data.get('cited', '0')),
                    url=data.get('url', ''),
                    crawl_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                if paper.is_valid():
                    papers.append(paper)
            
            # 构建搜索结果
            result = SearchResult(
                query=keyword,
                total_count=len(papers),
                papers=papers,
                search_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                page=1,
                page_size=len(papers)
            )
        
        self.logger.info(f"搜索完成: 找到 {len(papers)} 条结果, 耗时 {timer}")
        
        # 更新缓存
        self._papers_cache.extend(papers)
        
        return result
    
    def check_connection(self) -> bool:
        """检查知网连接"""
        try:
            browser = self._get_browser()
            return browser.check_connection()
        except Exception as e:
            self.logger.error(f"连接检查失败: {e}")
            return False
    
    def get_cached_papers(self) -> List[Paper]:
        """获取缓存的论文列表"""
        return self._papers_cache.copy()
    
    def clear_cache(self):
        """清空缓存"""
        self._papers_cache.clear()
        self.logger.info("缓存已清空")
    
    def close(self):
        """关闭浏览器"""
        if self._browser:
            self._browser.close()
            self._browser = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @property
    def total_cached(self) -> int:
        """获取缓存总数"""
        return len(self._papers_cache)
