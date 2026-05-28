#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知网爬虫主程序
"""

import sys
import argparse
from typing import Optional

from config.settings import settings, search_config, storage_config
from core.crawler import CNKIBrowser
from core.searcher import CNKISearcher
from models.paper import Paper, SearchResult
from utils.helpers import (
    setup_logger, 
    save_to_csv, 
    save_to_json, 
    ensure_dir,
    Timer
)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="知网(CNKI)学术文献爬虫工具 - Selenium版本",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--output", type=str, default="./output", help="输出目录")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索学术文献")
    search_parser.add_argument("keyword", type=str, help="搜索关键词")
    search_parser.add_argument("-p", "--pages", type=int, default=5, help="搜索页数 (默认: 5)")
    search_parser.add_argument("-t", "--type", type=str, 
                              choices=["journal", "thesis", "conference", "newspaper"], 
                              help="文献类型")
    search_parser.add_argument("-s", "--sort", type=str, default="relevance", 
                              choices=["relevance", "date", "cite", "download"],
                              help="排序方式")
    search_parser.add_argument("-f", "--format", type=str, default="csv", 
                              choices=["csv", "json", "xlsx"],
                              help="导出格式")
    
    # check 命令
    subparsers.add_parser("check", help="检查知网连接状态")
    
    return parser


def cmd_search(args) -> int:
    """执行搜索命令"""
    logger = setup_logger("search")
    
    logger.info("=" * 50)
    logger.info("知网文献搜索 (Selenium模式)")
    logger.info("=" * 50)
    logger.info(f"关键词: {args.keyword}")
    logger.info(f"页数: {args.pages}")
    logger.info(f"文献类型: {args.type or '全部'}")
    logger.info("注意: 将打开浏览器窗口，请勿关闭！")
    logger.info("=" * 50)
    
    searcher = CNKISearcher(settings, search_config)
    
    try:
        with Timer() as timer:
            result = searcher.search(
                keyword=args.keyword,
                pages=args.pages,
                literature_type=args.type,
                sort_by=args.sort
            )
        
        logger.info(f"搜索完成: 找到 {len(result.papers)} 条结果, 耗时 {timer}")
        
        if result.papers:
            ensure_dir(args.output)
            export_data = [paper.to_dict() for paper in result.papers]
            safe_keyword = args.keyword.replace("/", "_").replace("\\", "_")
            filename_base = f"cnki_{safe_keyword}"
            
            if args.format == "json":
                filepath = f"{args.output}/{filename_base}.json"
                success = save_to_json(result.to_dict(), filepath)
            else:
                filepath = f"{args.output}/{filename_base}.csv"
                success = save_to_csv(export_data, filepath)
            
            if success:
                logger.info(f"数据已保存至: {filepath}")
            else:
                logger.error("数据保存失败")
                return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"搜索出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        searcher.close()


def cmd_check(args) -> int:
    """执行检查命令"""
    logger = setup_logger("check")
    logger.info("正在检查知网连接...")
    
    try:
        browser = CNKIBrowser(settings, headless=False)
        if browser.check_connection():
            logger.info("✓ 知网连接正常")
            browser.close()
            return 0
        else:
            logger.error("✗ 知网连接失败")
            browser.close()
            return 1
    except Exception as e:
        logger.error(f"检查失败: {e}")
        return 1


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    if args.command == "search":
        return cmd_search(args)
    elif args.command == "check":
        return cmd_check(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
