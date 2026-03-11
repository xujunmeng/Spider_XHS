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
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from xhs_utils.common_util import init
from search_crawler.config import DB_CONFIG, EMAIL_CONFIG, CRAWL_CONFIG
from search_crawler.crawler_incremental import IncrementalCommentSpider


class CrawlerScheduler:
    """爬虫定时调度器"""
    
    def __init__(self):
        # 从配置读取调度参数
        from apscheduler.executors.pool import ThreadPoolExecutor
        executors = {
            'default': ThreadPoolExecutor(max_workers=CRAWL_CONFIG.get('thread_pool_workers', 10))
        }
        job_defaults = {
            'coalesce': CRAWL_CONFIG.get('coalesce', True),
            'max_instances': CRAWL_CONFIG.get('max_instances', 1),
            'misfire_grace_time': CRAWL_CONFIG.get('misfire_grace_time', 3600)
        }
        self.scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)
        self.spider = None
        self.running = False
        
        # ============================================
        # ✅ 复用：调用 init() 获取 cookies_str 和 base_path
        # ============================================
        cookies_str, base_path = init()
        logger.info(f"Excel保存路径: {base_path['excel']}")
        
        # 初始化爬虫
        self.spider = IncrementalCommentSpider(
            db_url=DB_CONFIG['url'],
            base_path=base_path,  # ✅ 复用：传入 base_path，用于Excel保存
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
        
        # 计算并显示调度规则
        interval_seconds = CRAWL_CONFIG.get('schedule_interval', 3600)
        interval_minutes = interval_seconds / 60
        
        # 根据间隔选择合适的触发器
        if interval_seconds < 3600:
            # 小于1小时，使用 IntervalTrigger（固定间隔）
            trigger = IntervalTrigger(seconds=interval_seconds)
            logger.info(f"定时规则: 每{interval_minutes:.0f}分钟执行一次 (固定间隔)")
        else:
            # 1小时及以上，使用 CronTrigger（整点执行）
            cron_minute = CRAWL_CONFIG.get('schedule_cron', '0')
            trigger = CronTrigger(minute=cron_minute)
            logger.info(f"定时规则: 每{interval_minutes/60:.0f}小时执行一次 (cron: {cron_minute}分)")
        
        logger.info(f"容错配置: misfire_grace_time={CRAWL_CONFIG.get('misfire_grace_time', 3600)}s, coalesce={CRAWL_CONFIG.get('coalesce', True)}")
        
        self.scheduler.add_job(
            self.run_crawl_job,
            trigger=trigger,
            id='crawler_hourly_job',
            replace_existing=True,
            max_instances=CRAWL_CONFIG.get('max_instances', 1),
            coalesce=CRAWL_CONFIG.get('coalesce', True),
            misfire_grace_time=CRAWL_CONFIG.get('misfire_grace_time', 3600)
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
