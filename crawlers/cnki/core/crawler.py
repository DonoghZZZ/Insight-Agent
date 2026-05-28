"""
知网爬虫核心模块 - 多浏览器支持版本
支持 Chrome/Firefox/Safari
"""

import time
import random
import re
import platform
import subprocess
from typing import Optional, Dict, Any, List

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from config.settings import Settings
from utils.helpers import setup_logger, clean_text, Timer


class CNKIBrowser:
    """
    知网浏览器爬虫类
    使用Selenium WebDriver处理JavaScript动态内容
    """
    
    BASE_URL = "https://kns.cnki.net"
    SEARCH_URL = "https://kns.cnki.net/kns8s/defaultresult/index"
    
    def __init__(self, settings: Optional[Settings] = None, headless: bool = False, browser: str = "auto"):
        """
        初始化浏览器
        
        Args:
            settings: 配置对象
            headless: 是否使用无头模式
            browser: 浏览器类型 "chrome", "firefox", "safari", "edge", "auto"
        """
        self.settings = settings or Settings()
        self.logger = setup_logger(self.__class__.__name__)
        self.headless = headless
        self.browser_type = browser
        self.driver = None
        
        if not SELENIUM_AVAILABLE:
            self.logger.error("Selenium未安装，请运行: pip install selenium")
            raise ImportError("需要安装selenium: pip install selenium")
        
        self._init_driver()
    
    def _check_browser(self) -> str:
        """检测可用浏览器"""
        if self.browser_type != "auto":
            return self.browser_type
        
        system = platform.system()
        
        # macOS优先Safari
        if system == "Darwin":
            try:
                subprocess.run(["osascript", "-e", "tell application \"Safari\" to quit"], 
                             capture_output=True, timeout=2)
                return "safari"
            except Exception as e:
                self.logger.debug(f"Safari检查失败: {e}")
        
        # Windows优先Edge
        if system == "Windows":
            return "edge"
        
        # Linux优先Firefox
        if system == "Linux":
            return "firefox"
        
        return "chrome"
    
    def _init_driver(self):
        """初始化浏览器驱动"""
        browser = self._check_browser()
        self.logger.info(f"使用浏览器: {browser}")
        
        try:
            if browser == "chrome":
                self._init_chrome()
            elif browser == "firefox":
                self._init_firefox()
            elif browser == "safari":
                self._init_safari()
            elif browser == "edge":
                self._init_edge()
            else:
                raise Exception(f"不支持的浏览器: {browser}")
                
            self.logger.info(f"{browser} 浏览器驱动初始化成功")
            
        except Exception as e:
            self.logger.error(f"浏览器驱动初始化失败: {e}")
            raise
    
    def _init_chrome(self):
        """初始化Chrome"""
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.chrome.service import Service as ChromeService
        
        options = ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # 尝试使用webdriver-manager
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            self.logger.warning(f"Chrome驱动初始化失败: {e}")
            self.driver = webdriver.Chrome(options=options)
    
    def _init_firefox(self):
        """初始化Firefox"""
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        
        options = FirefoxOptions()
        if self.headless:
            options.add_argument('--headless')
        
        try:
            from webdriver_manager.firefox import GeckoDriverManager
            from selenium.webdriver.firefox.service import Service as FirefoxService
            service = FirefoxService(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
        except Exception as e:
            self.logger.warning(f"Firefox驱动初始化失败: {e}")
            self.driver = webdriver.Firefox(options=options)
    
    def _init_safari(self):
        """初始化Safari"""
        self.driver = webdriver.Safari()
        # Safari不需要额外配置
    
    def _init_edge(self):
        """初始化Edge"""
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from selenium.webdriver.edge.service import Service as EdgeService
        
        options = EdgeOptions()
        options.add_argument('--disable-gpu')
        if self.headless:
            options.add_argument('--headless=new')
        
        try:
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            service = EdgeService(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=options)
        except Exception as e:
            self.logger.warning(f"使用webdriver-manager失败，使用本地驱动: {e}")
            self.driver = webdriver.Edge(options=options)
    
    def search(self, keyword: str, pages: int = 5, literature_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索论文
        """
        self.logger.info(f"开始搜索: {keyword}")
        
        results = []
        
        try:
            self.driver.get(self.SEARCH_URL)
            time.sleep(3)
            
            self._input_keyword(keyword)
            time.sleep(1)
            
            self._click_search_button()
            self._wait_for_results()
            
            for page in range(pages):
                self.logger.info(f"正在解析第 {page + 1} 页...")
                
                papers = self._parse_current_page()
                results.extend(papers)
                self.logger.info(f"第 {page + 1} 页: 获取 {len(papers)} 条记录")
                
                if page < pages - 1:
                    if not self._click_next_page():
                        break
                    time.sleep(2)
            
            self.logger.info(f"搜索完成，共获取 {len(results)} 条记录")
            
        except Exception as e:
            self.logger.error(f"搜索过程出错: {e}")
            import traceback
            traceback.print_exc()
            
        return results
    
    def _input_keyword(self, keyword: str):
        """输入搜索关键词"""
        try:
            # 多种选择器
            selectors = [
                'input[data-tipid="gradetxt-1"]',
                'input[aria-label="主题词"]',
                'input[id*="keyword"]',
                'input.txtinput',
                '#txt_search',
                'input.txt_input'
            ]
            
            input_box = None
            for selector in selectors:
                try:
                    input_box = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if input_box.is_displayed():
                        break
                except NoSuchElementException:
                    continue
            
            if input_box:
                input_box.clear()
                input_box.send_keys(keyword)
                self.logger.debug(f"已输入关键词: {keyword}")
            else:
                self.logger.warning("未找到搜索输入框")
                
        except Exception as e:
            self.logger.warning(f"输入关键词失败: {e}")
    
    def _click_search_button(self):
        """点击搜索按钮"""
        try:
            selectors = [
                'button[id="btnSearch"]',
                'a.btnSearch',
                '.search-btn',
                'button:contains("搜索")'
            ]
            
            for selector in selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn.is_displayed():
                        btn.click()
                        return
                except NoSuchElementException:
                    continue
            
            # JS点击
            self.driver.execute_script("document.getElementById('btnSearch').click()")
            
        except Exception as e:
            self.logger.warning(f"点击搜索按钮失败: {e}")
    
    def _wait_for_results(self, timeout: int = 15):
        """等待搜索结果加载"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table, #contentTable, .result'))
            )
            time.sleep(2)
            
        except TimeoutException:
            self.logger.warning("等待结果超时")
            time.sleep(3)
    
    def _parse_current_page(self) -> List[Dict[str, Any]]:
        """解析当前页面的论文列表"""
        papers = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # 尝试多种表格结构
            selectors = [
                'table.gridtable tbody tr',
                '#contentTable tr',
                '.result-table tr',
                'tr[class*="item"]',
                '.article-list tr',
                'table tr',
            ]
            
            rows = []
            for selector in selectors:
                rows = soup.select(selector)
                if rows and len(rows) > 1:
                    break
            
            for row in rows:
                try:
                    paper = self._parse_row(row)
                    if paper and paper.get('title'):
                        papers.append(paper)
                except Exception as e:
                    self.logger.debug(f"解析行失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"解析页面失败: {e}")
        
        return papers
    
    def _parse_row(self, row) -> Dict[str, Any]:
        """解析单行论文数据"""
        paper = {}
        
        try:
            # 标题
            title_el = row.select_one('a.fz14, a[class*="title"], .title a, a')
            if title_el:
                paper['title'] = clean_text(title_el.get_text())
                paper['url'] = title_el.get('href', '') if title_el else ''
            
            # 作者
            author_el = row.select_one('td.author, .author, [class*="author"]')
            paper['authors'] = clean_text(author_el.get_text()) if author_el else ''
            
            # 来源
            source_el = row.select_one('td.source, .source, [class*="source"]')
            paper['source'] = clean_text(source_el.get_text()) if source_el else ''
            
            # 日期
            date_el = row.select_one('td.date, .date, [class*="date"]')
            paper['date'] = clean_text(date_el.get_text()) if date_el else ''
            
            # 被引
            cite_el = row.select_one('td[nowrap], [class*="cite"]')
            if cite_el:
                text = clean_text(cite_el.get_text())
                match = re.search(r'\d+', text)
                paper['cited'] = match.group() if match else '0'
            else:
                paper['cited'] = '0'
                
        except Exception:
            pass
        
        return paper
    
    def _click_next_page(self) -> bool:
        """点击下一页"""
        try:
            selectors = ['#PageNext', 'a[id="PageNext"]', '.page-next']
            
            for selector in selectors:
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn.is_displayed():
                        classes = next_btn.get_attribute('class') or ''
                        if 'disabled' not in classes:
                            next_btn.click()
                            time.sleep(2)
                            return True
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.warning(f"点击下一页失败: {e}")
            return False
    
    def check_connection(self) -> bool:
        """检查知网连接"""
        try:
            self.driver.get(self.BASE_URL)
            time.sleep(3)
            return "cnki" in self.driver.current_url.lower()
        except Exception:
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.warning(f"关闭浏览器失败: {e}")
            self.logger.info("浏览器已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 兼容别名
CNKICrawler = CNKIBrowser
