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
from xhs_utils.common_util import init


def main():
    """主入口"""
    # 初始化
    cookies_str, base_path = init()
    
    # 创建爬虫实例
    spider = IncrementalCommentSpider(
        db_url=DB_CONFIG['url'],
        email_config=EMAIL_CONFIG if EMAIL_CONFIG.get('sender_email') else None,
        use_mock_email=False
    )
    
    # 执行采集
    keyword = CRAWL_CONFIG['keyword']
    max_pages = CRAWL_CONFIG['max_pages']
    
    print(f"开始采集 | 关键词: {keyword} | 页数: {max_pages}")
    
    try:
        notes, comments = spider.run_incremental_crawl(
            keyword=keyword,
            max_pages=max_pages,
            cookies_str=cookies_str
        )
        print(f"采集完成 | 笔记: {len(notes)} | 新增评论: {len(comments)}")
    except Exception as e:
        print(f"采集失败: {e}")


if __name__ == '__main__':
    main()
