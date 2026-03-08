#!/usr/bin/env python3
# ============================================
# 启动单次采集
# ============================================

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search_crawler.crawler_incremental import IncrementalCommentSpider
from search_crawler.config import DB_CONFIG, EMAIL_CONFIG, CRAWL_CONFIG


def main():
    """主入口"""
    # 创建爬虫实例（自动从 config.py 同步 cookies 到数据库）
    spider = IncrementalCommentSpider(
        db_url=DB_CONFIG['url'],
        email_config=EMAIL_CONFIG if EMAIL_CONFIG.get('sender_email') else None,
        use_mock_email=False
    )
    
    # 执行采集（不传 cookies_str，让爬虫从 CookiePool 获取）
    keyword = CRAWL_CONFIG['keyword']
    max_pages = CRAWL_CONFIG['max_pages']
    
    print(f"开始采集 | 关键词: {keyword} | 页数: {max_pages}")
    print(f"提示: 爬虫将使用 config.py 中配置的 Cookie（已同步到数据库）")
    
    try:
        notes, comments = spider.run_incremental_crawl(
            keyword=keyword,
            max_pages=max_pages
            # 不传 cookies_str，让爬虫从 CookiePoolManager 获取
        )
        print(f"采集完成 | 笔记: {len(notes)} | 新增评论: {len(comments)}")
    except Exception as e:
        print(f"采集失败: {e}")


if __name__ == '__main__':
    main()
