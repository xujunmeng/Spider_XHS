#!/usr/bin/env python3
# ============================================
# 定时任务调度器 - 每小时执行一次采集
# ============================================

import sys
import os
import time
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from .config import DB_CONFIG, EMAIL_CONFIG, CRAWL_CONFIG
from .crawler_incremental import IncrementalCommentSpider


class CrawlerScheduler:
    """爬虫定时调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.spider = None
        self.running = False
        
        # 初始化爬虫
        self.spider = IncrementalCommentSpider(
            db_url=DB_CONFIG['url'],
            email_config=EMAIL_CONFIG if EMAIL_CONFIG.get('sender_email') else None,
            use_mock_email=False
        )
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """处理终止信号"""
        logger.info("收到终止信号，正在关闭调度器...")
        self.shutdown()
        sys.exit(0)
    
    def run_crawl_job(self):
        """执行采集任务"""
        if self.running:
            logger.warning("上次任务仍在运行，跳过本次执行")
            return
        
        self.running = True
        
        try:
            logger.info("=== 定时任务开始执行 ===")
            
            keyword = CRAWL_CONFIG['keyword']
            max_pages = CRAWL_CONFIG['max_pages']
            
            notes, comments = self.spider.run_incremental_crawl(
                keyword=keyword,
                max_pages=max_pages
            )
            
            logger.info(f"=== 定时任务执行完成 | 新增评论: {len(comments)} 条 ===")
            
        except Exception as e:
            logger.error(f"定时任务执行失败: {e}")
        finally:
            self.running = False
    
    def start(self):
        """启动定时任务"""
        logger.info("启动定时任务调度器...")
        logger.info(f"采集关键词: {CRAWL_CONFIG['keyword']}")
        logger.info(f"采集页数: {CRAWL_CONFIG['max_pages']}")
        logger.info("定时规则: 每小时执行一次")
        
        # 添加定时任务（每小时的第0分钟执行）
        trigger = CronTrigger(minute='0')
        
        self.scheduler.add_job(
            self.run_crawl_job,
            trigger=trigger,
            id='crawler_hourly_job',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("定时任务调度器已启动")
        
        # 立即执行一次
        logger.info("立即执行首次采集...")
        self.run_crawl_job()
        
        # 保持程序运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        """关闭调度器"""
        logger.info("正在关闭调度器...")
        if self.scheduler.running:
            self.scheduler.shutdown()
        logger.info("调度器已关闭")


def main():
    """主入口"""
    scheduler = CrawlerScheduler()
    scheduler.start()


if __name__ == '__main__':
    main()
