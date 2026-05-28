#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣爬虫通用框架 v3.0
==================
交互式菜单版：用户选择要爬取的内容
Author: 糯糯
Date: 2026-04-04
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ==================== 配置区 ====================
class Config:
    MIN_DELAY = 3
    MAX_DELAY = 8

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://book.douban.com/',
    }

    PROXY = None
    OUTPUT_DIR = Path(__file__).parent / 'output'
    OUTPUT_DIR.mkdir(exist_ok=True)


# ==================== 爬虫核心 ====================
class DoubanCrawler:
    """豆瓣爬虫"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(Config.HEADERS)
        self.session.cookies.set('bid', self._generate_bid(), domain='.douban.com')

    def _generate_bid(self) -> str:
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

    def _random_delay(self):
        time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))

    def _fetch(self, url: str, retries: int = 3) -> Optional[str]:
        for i in range(retries):
            try:
                response = self.session.get(url, proxies=Config.PROXY, timeout=15)
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    return response.text
                elif response.status_code == 418:
                    print(f"⚠️ 反爬触发，等待60秒...")
                    time.sleep(60)
            except Exception as e:
                print(f"⚠️ 请求失败 ({i+1}/{retries}): {e}")
                time.sleep(5)
        return None

    # ===== 图书Top250 =====
    def crawl_books_top250(self, pages: int = 10) -> List[Dict]:
        books = []
        print(f"\n📚 正在爬取豆瓣图书Top250...")

        for page in range(pages):
            url = f"https://book.douban.com/top250?start={page * 25}" if page > 0 else "https://book.douban.com/top250"
            print(f"   第 {page + 1}/{pages} 页...", end=" ")

            html = self._fetch(url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('tr.item')

            for item in items:
                book = self._parse_book_item(item)
                if book:
                    books.append(book)

            print(f"已获取 {len(books)} 本")
            self._random_delay()

        # 添加排名
        for i, book in enumerate(books, 1):
            book['排名'] = i

        print(f"✅ 共获取 {len(books)} 本图书")
        return books

    def _parse_book_item(self, item) -> Optional[Dict]:
        book = {
            '排名': 0, '书名': '', '作者': '', '出版社': '',
            '出版年份': '', '定价': '', '评分': 0.0,
            '评价人数': 0, '五星比例': '', '四星比例': '',
            '三星比例': '', '简介': '', '详情页': '',
            '爬取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            # 书名
            title_elem = item.select_one('.pl2 a')
            if title_elem:
                book['书名'] = title_elem.get_text(strip=True).replace('/', '').replace(' ', '')
                book['详情页'] = title_elem.get('href', '')

            # 出版信息
            pub_elem = item.select_one('.pl')
            if pub_elem:
                pub_text = pub_elem.get_text(strip=True)
                parts = pub_text.split('/')
                if parts:
                    book['作者'] = parts[0].strip()
                # 提取出版社、年份、价格
                for part in parts[1:]:
                    part = part.strip()
                    if re.match(r'\d{4}', part):
                        book['出版年份'] = part[:4]
                    elif '元' in part or '¥' in part:
                        book['定价'] = part
                    elif not book['出版社']:
                        book['出版社'] = part

            # 评分
            rating_elem = item.select_one('.rating_nums')
            if rating_elem:
                try:
                    book['评分'] = float(rating_elem.get_text(strip=True))
                except Exception as e:
                    logger.warning(f"解析评分失败: {e}")

            # 评价人数
            pl_elems = item.select('.pl')
            for pl in pl_elems:
                match = re.search(r'(\d+)人评价', pl.get_text())
                if match:
                    book['评价人数'] = int(match.group(1))
                    break

            # 星级分布
            star_elem = item.select_one('.rating_sum')
            if star_elem:
                ratios = star_elem.select('.rating_per')
                if len(ratios) >= 3:
                    book['五星比例'] = ratios[0].get_text(strip=True)
                    book['四星比例'] = ratios[1].get_text(strip=True)
                    book['三星比例'] = ratios[2].get_text(strip=True)

            # 简介
            quote_elem = item.select_one('.quote')
            if quote_elem:
                book['简介'] = quote_elem.get_text(strip=True)

        except Exception as e:
            pass

        return book if book['书名'] else None

    # ===== 图书标签 =====
    def crawl_books_by_tag(self, tag: str, pages: int = 5) -> List[Dict]:
        books = []
        print(f"\n🏷️ 正在爬取标签「{tag}」的图书...")

        for page in range(pages):
            url = f"https://book.douban.com/tag/{tag}?start={page * 20}&type=T"
            print(f"   第 {page + 1}/{pages} 页...", end=" ")

            html = self._fetch(url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.subject-item')

            for item in items:
                book = self._parse_tag_book(item, tag)
                if book:
                    books.append(book)

            print(f"已获取 {len(books)} 本")
            self._random_delay()

        for i, book in enumerate(books, 1):
            book['序号'] = i

        print(f"✅ 共获取 {len(books)} 本图书")
        return books

    def _parse_tag_book(self, item, tag: str) -> Optional[Dict]:
        book = {
            '序号': 0, '书名': '', '作者': '', '出版社': '',
            '出版年份': '', '评分': 0.0, '评价人数': 0,
            '标签': tag, '详情页': '',
            '爬取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            # 书名
            title_elem = item.select_one('.pl2 a')
            if title_elem:
                book['书名'] = title_elem.get_text(strip=True).replace('/', '').replace(' ', '')
                book['详情页'] = title_elem.get('href', '')

            # 出版信息
            pub_elem = item.select_one('.pub')
            if pub_elem:
                pub_text = pub_elem.get_text(strip=True)
                parts = pub_text.split('/')
                if parts:
                    book['作者'] = parts[0].strip()
                for part in parts[1:]:
                    part = part.strip()
                    if re.match(r'\d{4}', part):
                        book['出版年份'] = part[:4]
                    elif not book['出版社']:
                        book['出版社'] = part

            # 评分
            rating_elem = item.select_one('.rating_nums')
            if rating_elem:
                try:
                    book['评分'] = float(rating_elem.get_text(strip=True))
                except Exception as e:
                    logger.warning(f"解析评分失败: {e}")

            # 评价人数
            count_elem = item.select_one('.pl')
            if count_elem:
                match = re.search(r'(\d+)', count_elem.get_text())
                if match:
                    book['评价人数'] = int(match.group(1))

        except Exception as e:
            logger.warning(f"解析标签图书条目失败: {e}")

        return book if book['书名'] else None

    # ===== 电影Top250 =====
    def crawl_movies_top250(self, pages: int = 10) -> List[Dict]:
        movies = []
        print(f"\n🎬 正在爬取豆瓣电影Top250...")

        for page in range(pages):
            url = f"https://movie.douban.com/top250?start={page * 25}" if page > 0 else "https://movie.douban.com/top250"
            print(f"   第 {page + 1}/{pages} 页...", end=" ")

            html = self._fetch(url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.item')

            for item in items:
                movie = self._parse_movie_item(item)
                if movie:
                    movies.append(movie)

            print(f"已获取 {len(movies)} 部")
            self._random_delay()

        for i, movie in enumerate(movies, 1):
            movie['排名'] = i

        print(f"✅ 共获取 {len(movies)} 部电影")
        return movies

    def _parse_movie_item(self, item) -> Optional[Dict]:
        movie = {
            '排名': 0, '电影名称': '', '导演': '', '主演': '',
            '类型': '', '年份': '', '国家': '',
            '评分': 0.0, '评价人数': 0, '简介': '',
            '详情页': '', '爬取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            # 标题
            title_elem = item.select_one('.hd .title')
            if title_elem:
                movie['电影名称'] = title_elem.get_text(strip=True)

            # 详情页
            link_elem = item.select_one('.hd a')
            if link_elem:
                movie['详情页'] = link_elem.get('href', '')

            # 信息行
            info_elem = item.select_one('.bd p')
            if info_elem:
                info_text = info_elem.get_text(strip=True)
                lines = info_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if '导演' in line:
                        movie['导演'] = line.replace('导演:', '').strip()
                    elif '主演' in line:
                        movie['主演'] = line.replace('主演:', '').strip()
                    elif '/' in line:
                        parts = [p.strip() for p in line.split('/')]
                        for p in parts:
                            if re.match(r'\d{4}', p):
                                movie['年份'] = p[:4]
                            elif p in ['电影', '纪录片', '动画', '短片']:
                                pass
                            elif len(p) < 10 and not movie['类型']:
                                movie['类型'] = p

            # 评分
            rating_elem = item.select_one('.star .rating_num')
            if rating_elem:
                try:
                    movie['评分'] = float(rating_elem.get_text(strip=True))
                except Exception as e:
                    logger.warning(f"解析评分失败: {e}")

            # 评价人数
            star_elem = item.select_one('.star')
            if star_elem:
                match = re.search(r'(\d+)人评价', star_elem.get_text())
                if match:
                    movie['评价人数'] = int(match.group(1))

            # 简介
            quote_elem = item.select_one('.quote')
            if quote_elem:
                movie['简介'] = quote_elem.get_text(strip=True)

        except Exception as e:
            logger.warning(f"解析电影条目失败: {e}")

        return movie if movie['电影名称'] else None

    # ===== 关键词搜索 =====
    def crawl_books_by_keyword(self, keyword: str, pages: int = 3) -> List[Dict]:
        books = []
        print(f"\n🔍 正在搜索「{keyword}」相关图书...")

        for page in range(pages):
            url = f"https://book.douban.com/search?q={keyword}&start={page * 20}"
            print(f"   第 {page + 1}/{pages} 页...", end=" ")

            html = self._fetch(url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.result')

            for item in items:
                book = self._parse_search_book(item, keyword)
                if book:
                    books.append(book)

            print(f"已获取 {len(books)} 本")
            self._random_delay()

        for i, book in enumerate(books, 1):
            book['序号'] = i

        print(f"✅ 共获取 {len(books)} 本图书")
        return books

    def _parse_search_book(self, item, keyword: str) -> Optional[Dict]:
        book = {
            '序号': 0, '书名': '', '作者': '', '评分': 0.0,
            '评价人数': 0, '搜索词': keyword, '详情页': '',
            '爬取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            title_elem = item.select_one('.title')
            if title_elem:
                book['书名'] = title_elem.get_text(strip=True).replace('/', '')

            link_elem = item.select_one('a[href*="/subject/"]')
            if link_elem:
                book['详情页'] = link_elem.get('href', '')

            rating_elem = item.select_one('.rating_nums')
            if rating_elem:
                try:
                    book['评分'] = float(rating_elem.get_text(strip=True))
                except Exception as e:
                    logger.warning(f"解析评分失败: {e}")

            count_elem = item.select_one('.muti')
            if count_elem:
                match = re.search(r'(\d+)', count_elem.get_text())
                if match:
                    book['评价人数'] = int(match.group(1))

        except Exception as e:
            logger.warning(f"解析搜索结果失败: {e}")

        return book if book['书名'] else None

    # ===== 保存功能 =====
    def save(self, data: List[Dict], filename: str):
        if not data:
            print("⚠️ 没有数据可保存")
            return

        output_dir = getattr(self, 'output_dir_override', None) or Config.OUTPUT_DIR
        filepath = output_dir / filename

        # 优先保存Excel
        try:
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False, engine='openpyxl')
            print(f"💾 已保存到: {filepath}")
        except Exception as e:
            # 降级为CSV
            csv_path = filepath.with_suffix('.csv')
            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"💾 已保存到: {csv_path}")


# ==================== 交互式菜单 ====================
def show_menu():
    """显示主菜单"""
    print("\n" + "=" * 50)
    print("       📚 豆瓣数据爬虫 - 请选择要爬取的内容")
    print("=" * 50)
    print("")
    print("  【图书数据】")
    print("    1️⃣  图书 Top250 排行榜")
    print("    2️⃣  按标签爬取图书（如：Python、数据科学）")
    print("    3️⃣  按关键词搜索图书")
    print("")
    print("  【电影数据】")
    print("    4️⃣  电影 Top250 排行榜")
    print("")
    print("  【组合爬取】")
    print("    5️⃣  同时爬取图书Top250 + 电影Top250")
    print("")
    print("    0️⃣  退出")
    print("")
    print("=" * 50)


def get_pages_input(prompt: str = "请输入要爬取的页数") -> int:
    """获取页数输入"""
    while True:
        try:
            pages = input(f"📖 {prompt} (1-10，建议5): ").strip()
            if not pages:
                return 5
            pages = int(pages)
            if 1 <= pages <= 10:
                return pages
            print("⚠️ 请输入1-10之间的数字")
        except ValueError:
            print("⚠️ 请输入有效数字")


def get_tag_input() -> str:
    """获取标签输入"""
    print("\n🏷️  常用标签推荐：")
    print("   Python, 机器学习, 数据科学, 人工智能, 信息检索,")
    print("   心理学, 哲学, 历史, 文学, 经济学, 编程, 数据库")
    print("")
    while True:
        tag = input("📝 请输入要爬取的标签: ").strip()
        if tag:
            return tag
        print("⚠️ 标签不能为空")


def get_keyword_input() -> str:
    """获取关键词输入"""
    print("\n🔍 请输入搜索关键词")
    while True:
        keyword = input("📝 请输入搜索关键词: ").strip()
        if keyword:
            return keyword
        print("⚠️ 关键词不能为空")


def run_cli(args):
    """CLI 非交互模式"""
    crawler = DoubanCrawler()

    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        crawler.output_dir_override = output_dir
    else:
        crawler.output_dir_override = None

    pages = args.pages

    if args.mode == 'book_top250':
        data = crawler.crawl_books_top250(pages)
        if data:
            crawler.save(data, 'books_top250.xlsx')
    elif args.mode == 'movie_top250':
        data = crawler.crawl_movies_top250(pages)
        if data:
            crawler.save(data, 'movies_top250.xlsx')
    elif args.mode == 'book_tag':
        if not args.keyword:
            print("❌ book_tag 模式需要 --keyword 参数")
            sys.exit(1)
        data = crawler.crawl_books_by_tag(args.keyword, pages)
        if data:
            crawler.save(data, f'books_tag_{args.keyword}.xlsx')
    elif args.mode == 'book_search':
        if not args.keyword:
            print("❌ book_search 模式需要 --keyword 参数")
            sys.exit(1)
        data = crawler.crawl_books_by_keyword(args.keyword, pages)
        if data:
            crawler.save(data, f'books_search_{args.keyword}.xlsx')


# ==================== 主程序 ====================
if __name__ == "__main__":
    import sys

    parser = argparse.ArgumentParser(description="豆瓣爬虫通用框架 v3.0", add_help=False)
    parser.add_argument("--mode", choices=['book_top250', 'movie_top250', 'book_tag', 'book_search'], help="运行模式")
    parser.add_argument("--keyword", help="搜索关键词或标签")
    parser.add_argument("--pages", type=int, default=5, help="爬取页数(默认5)")
    parser.add_argument("--output", help="输出目录")
    cli_args, _ = parser.parse_known_args()

    if cli_args.mode:
        run_cli(cli_args)
    else:
        print("\n" + "=" * 50)
        print("    🎯 豆瓣爬虫通用框架 v3.0")
        print("    📊 支持图书/电影/标签/关键词")
        print("=" * 50)

        crawler = DoubanCrawler()

        while True:
            show_menu()
            choice = input("👉 请选择 (0-5): ").strip()

            if choice == '0':
                print("\n👋 再见！")
                break

            elif choice == '1':
                pages = get_pages_input("图书Top250")
                data = crawler.crawl_books_top250(pages)
                if data:
                    crawler.save(data, 'books_top250.xlsx')
                input("\n按回车继续...")

            elif choice == '2':
                tag = get_tag_input()
                pages = get_pages_input(f"标签「{tag}」")
                data = crawler.crawl_books_by_tag(tag, pages)
                if data:
                    crawler.save(data, f'books_tag_{tag}.xlsx')
                input("\n按回车继续...")

            elif choice == '3':
                keyword = get_keyword_input()
                pages = get_pages_input("搜索结果")
                data = crawler.crawl_books_by_keyword(keyword, pages)
                if data:
                    crawler.save(data, f'books_search_{keyword}.xlsx')
                input("\n按回车继续...")

            elif choice == '4':
                pages = get_pages_input("电影Top250")
                data = crawler.crawl_movies_top250(pages)
                if data:
                    crawler.save(data, 'movies_top250.xlsx')
                input("\n按回车继续...")

            elif choice == '5':
                pages = get_pages_input("每个榜单")
                print("\n" + "-" * 40)
                books = crawler.crawl_books_top250(pages)
                if books:
                    crawler.save(books, 'books_top250.xlsx')
                print("-" * 40)
                movies = crawler.crawl_movies_top250(pages)
                if movies:
                    crawler.save(movies, 'movies_top250.xlsx')
                input("\n按回车继续...")

            else:
                print("⚠️ 无效选择，请输入0-5")
