#!/usr/bin/env python3
"""
京东评论爬虫 - 批量运行脚本
用法: python3 batch_run.py
"""
from run import (
    create_context, scrape_single, save_merged,
    OUTPUT_DIR, extract_product_id,
)
from playwright.sync_api import sync_playwright
from datetime import datetime
import os, sys, traceback

# ============ 配置：在此修改要爬取的商品 ============
PRODUCT_LIST = [
    # 帝泊洱系列（示例，请替换为实际链接或ID）
    "100249710729",  # 茉莉味6支装
    # "https://item.jd.com/10026793134282.html",  # 示例格式
    # "https://item.jd.com/100249710706.html",
    # 添加更多...
]

MAX_PER_PRODUCT = 100   # 每个商品最多评论数
RETRY_TIMES = 3         # 失败重试次数

# ========================================================


def main():
    all_data = {}
    total = len(PRODUCT_LIST)

    with sync_playwright() as p:
        ctx = create_context(p)
        page = ctx.new_page()

        for idx, product in enumerate(PRODUCT_LIST, 1):
            print(f"\n{'#' * 50}")
            print(f"# [{idx}/{total}] {product}")
            print(f"{'#' * 50}")

            pid = extract_product_id(product)
            if not pid:
                print(f"  ⚠️ 无法解析: {product}")
                continue

            reviews = None
            pinfo = None

            for attempt in range(RETRY_TIMES):
                try:
                    reviews, pinfo = scrape_single(page, pid, MAX_PER_PRODUCT)
                    break
                except KeyboardInterrupt:
                    print("\n⚠️ 用户中断，保存已有数据...")
                    ctx.close()
                    _save_and_exit(all_data)
                except Exception as e:
                    print(f"  ❌ 第{attempt+1}次尝试失败: {e}")
                    if attempt < RETRY_TIMES - 1:
                        print(f"  🔄 等待10秒后重试...")
                        import time; time.sleep(10)

            if reviews:
                name = pinfo.get('name', pid)
                for r in reviews:
                    r['product_name'] = name
                    r['product_id'] = pid
                all_data[name] = reviews
                print(f"  ✅ 完成: {name} ({len(reviews)}条)")
            else:
                print(f"  ❌ 失败: {pid}")

        ctx.close()

    # 保存合并总表
    if all_data:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged = os.path.join(OUTPUT_DIR, f"reviews_京东合集_{ts}.xlsx")
        save_merged(all_data, merged)
    else:
        print("⚠️ 未获取到任何评论数据")

    print("\n✨ 全部完成!")


def _save_and_exit(all_data):
    if all_data:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        merged = os.path.join(OUTPUT_DIR, f"reviews_京东合集_中断保存_{ts}.xlsx")
        save_merged(all_data, merged)
    sys.exit(0)


if __name__ == "__main__":
    main()
