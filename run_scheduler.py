#!/usr/bin/env python3
# ============================================
# 启动定时任务调度器
# ============================================

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search_crawler.scheduler import CrawlerScheduler


def main():
    """启动定时任务"""
    scheduler = CrawlerScheduler()
    scheduler.start()


if __name__ == '__main__':
    main()
