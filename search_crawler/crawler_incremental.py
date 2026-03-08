#!/usr/bin/env python3
# ============================================
# 小红书增量评论采集爬虫
# ============================================

import sys
import os
import time
import random
import hashlib
from datetime import datetime
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy import func

# 导入项目已有模块
from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.data_util import save_to_xlsx
from xhs_utils.common_util import init

# 导入本包模块
from .config import CRAWL_CONFIG, DELAY_CONFIG
from .models import DatabaseManager, CommentHistory, NoteHistory, CrawlLog
from .cookie_pool_manager import CookiePoolManager
from .email_notifier import EmailNotifier, EmailNotifierMock
from .config import COOKIE_POOL


class IncrementalCommentSpider:
    """增量评论采集爬虫"""
    
    def __init__(self, db_url, email_config=None, use_mock_email=False, auto_sync_cookies=True):
        """
        :param db_url: 数据库连接URL
        :param email_config: 邮件配置（可选）
        :param use_mock_email: 是否使用邮件模拟器（测试用）
        :param auto_sync_cookies: 是否自动同步 config.py 中的 Cookie 到数据库
        """
        # 注意：需先手动执行 SQL 初始化脚本创建表
        self.db_manager = DatabaseManager(db_url)
        self.cookie_manager = CookiePoolManager(self.db_manager)
        
        # 自动同步 config.py 中的 Cookie 到数据库
        if auto_sync_cookies:
            self._sync_cookies_from_config()
        
        # 初始化邮件通知器
        if email_config:
            if use_mock_email:
                self.email_notifier = EmailNotifierMock(email_config)
            else:
                self.email_notifier = EmailNotifier(email_config)
        else:
            self.email_notifier = None
        
        # 初始化小红书API
        self.xhs_apis = XHS_Apis()
    
    def _sync_cookies_from_config(self):
        """从 config.py 同步 Cookie 到数据库"""
        for cookie_info in COOKIE_POOL:
            cookie_value = cookie_info.get('value', '').strip()
            if cookie_value:
                self.cookie_manager.add_cookie(
                    cookie_info['name'],
                    cookie_value,
                    cookie_info.get('account_info', '')
                )
    
    def generate_comment_unique_id(self, comment):
        """生成评论唯一标识"""
        note_id = comment.get('note_id', '')
        comment_id = comment.get('comment_id', '')
        user_id = comment.get('user_id', '')
        content = comment.get('content', '')[:50]
        upload_time = comment.get('upload_time', '')
        
        unique_str = f"{note_id}_{comment_id}_{user_id}_{content}_{upload_time}"
        return hashlib.md5(unique_str.encode('utf-8')).hexdigest()
    
    def batch_check_exists(self, session, unique_ids):
        """批量检查评论是否存在，返回已存在的ID集合"""
        if not unique_ids:
            return set()
        
        results = session.query(CommentHistory.unique_id).filter(
            CommentHistory.unique_id.in_(unique_ids)
        ).all()
        return set(row[0] for row in results)
    
    def filter_new_comments(self, session, comments):
        """过滤出新增的评论"""
        for comment in comments:
            comment['_unique_id'] = self.generate_comment_unique_id(comment)
        
        unique_ids = [c['_unique_id'] for c in comments]
        exists_set = self.batch_check_exists(session, unique_ids)
        
        new_comments = [c for c in comments if c['_unique_id'] not in exists_set]
        return new_comments
    
    def save_comment_history_batch(self, session, comments):
        """批量保存评论历史记录"""
        if not comments:
            return 0
        
        comment_objects = []
        for comment in comments:
            ch = CommentHistory(
                unique_id=comment.get('_unique_id'),
                note_id=comment.get('note_id'),
                comment_id=comment.get('comment_id'),
                parent_comment_id=comment.get('parent_comment_id'),
                user_id=comment.get('user_id'),
                nickname=comment.get('nickname'),
                content=comment.get('content'),
                like_count=comment.get('like_count', 0),
                upload_time=comment.get('upload_time'),
                ip_location=comment.get('ip_location')
            )
            comment_objects.append(ch)
        
        session.bulk_save_objects(comment_objects)
        return len(comment_objects)
    
    def save_note_history(self, session, notes):
        """保存笔记历史记录（存在则更新）"""
        for note in notes:
            existing = session.query(NoteHistory).filter_by(
                note_id=note.get('note_id')
            ).first()
            
            if existing:
                existing.note_url = note.get('note_url')
                existing.title = note.get('title')
                existing.nickname = note.get('nickname')
                existing.liked_count = note.get('liked_count', 0)
                existing.collected_count = note.get('collected_count', 0)
                existing.comment_count = note.get('comment_count', 0)
                existing.share_count = note.get('share_count', 0)
            else:
                new_note = NoteHistory(
                    note_id=note.get('note_id'),
                    note_url=note.get('note_url'),
                    title=note.get('title'),
                    user_id=note.get('user_id'),
                    nickname=note.get('nickname'),
                    note_type=note.get('note_type'),
                    liked_count=note.get('liked_count', 0),
                    collected_count=note.get('collected_count', 0),
                    comment_count=note.get('comment_count', 0),
                    share_count=note.get('share_count', 0),
                    upload_time=note.get('upload_time')
                )
                session.add(new_note)
    
    def random_delay(self, min_seconds, max_seconds):
        """随机延迟"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def search_notes(self, query, page, sort_type=1, cookies_str=''):
        """搜索笔记"""
        try:
            success, msg, res_json = self.xhs_apis.search_note(
                query=query,
                cookies_str=cookies_str,
                page=page,
                sort_type_choice=sort_type
            )
            
            if not success:
                logger.error(f"搜索笔记失败: {msg}")
                return []
            
            items = res_json.get('data', {}).get('items', [])
            # 过滤只保留笔记类型
            notes = [item for item in items if item.get('model_type') == 'note']
            return notes
            
        except Exception as e:
            logger.error(f"搜索笔记异常: {e}")
            return []
    
    def get_all_comments(self, note_url, cookies_str=''):
        """获取笔记的所有评论"""
        try:
            success, msg, comments = self.xhs_apis.get_note_all_comment(
                url=note_url,
                cookies_str=cookies_str
            )
            
            if not success:
                logger.error(f"获取评论失败: {msg}")
                return []
            
            return comments if comments else []
            
        except Exception as e:
            logger.error(f"获取评论异常: {e}")
            return []
    
    def run_incremental_crawl(self, keyword=None, max_pages=None, cookies_str=''):
        """
        执行增量采集
        :param keyword: 搜索关键词（默认使用配置）
        :param max_pages: 最大采集页数（默认使用配置）
        :param cookies_str: Cookie字符串
        """
        keyword = keyword or CRAWL_CONFIG['keyword']
        max_pages = max_pages or CRAWL_CONFIG['max_pages']
        
        task_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        session = self.db_manager.get_session()
        
        try:
            # 记录任务开始
            crawl_log = CrawlLog(task_id=task_id, keyword=keyword, status=0)
            session.add(crawl_log)
            session.commit()
            
            logger.info(f"=== 开始增量采集 | 关键词: {keyword} | 任务ID: {task_id} ===")
            
            all_new_comments = []
            all_notes = []
            total_comments = 0
            
            # 1. 分页搜索笔记
            for page in range(1, max_pages + 1):
                logger.info(f"正在搜索第 {page} 页...")
                
                notes = self.search_notes(keyword, page, CRAWL_CONFIG['sort_type'], cookies_str)
                
                if not notes:
                    logger.info(f"第 {page} 页无数据，停止搜索")
                    break
                
                all_notes.extend(notes)
                logger.info(f"第 {page} 页获取 {len(notes)} 篇笔记")
                
                # 2. 采集每条笔记的评论
                for note in notes:
                    note_id = note.get('id')
                    xsec_token = note.get('xsec_token', '')
                    note_url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"
                    
                    logger.info(f"正在获取笔记评论: {note_id}")
                    
                    # 获取评论
                    comments = self.get_all_comments(note_url, cookies_str)
                    total_comments += len(comments)
                    
                    logger.info(f"笔记 {note_id} 共有 {len(comments)} 条评论")
                    
                    # 3. 过滤新增评论
                    new_comments = self.filter_new_comments(session, comments)
                    
                    if new_comments:
                        # 关联笔记信息
                        for comment in new_comments:
                            comment['note_id'] = note_id
                            comment['note_url'] = note_url
                            comment['note_title'] = note.get('title', '无标题')
                            comment['note_author'] = note.get('user', {}).get('nickname', '未知作者')
                            comment['note_author_id'] = note.get('user', {}).get('user_id', '')
                            comment['note_upload_time'] = note.get('time', '')
                        
                        all_new_comments.extend(new_comments)
                        
                        # 4. 批量保存到MySQL
                        self.save_comment_history_batch(session, new_comments)
                        session.commit()
                        
                        logger.info(f"笔记 {note_id} 新增 {len(new_comments)} 条评论")
                    
                    # 随机延迟
                    self.random_delay(*DELAY_CONFIG['note_interval'])
                
                # 页间延迟
                self.random_delay(*DELAY_CONFIG['page_interval'])
            
            # 5. 保存笔记历史
            notes_for_save = []
            for note in all_notes:
                notes_for_save.append({
                    'note_id': note.get('id'),
                    'note_url': f"https://www.xiaohongshu.com/explore/{note.get('id')}",
                    'title': note.get('title', '无标题'),
                    'user_id': note.get('user', {}).get('user_id', ''),
                    'nickname': note.get('user', {}).get('nickname', '未知作者'),
                    'note_type': '视频' if note.get('type') == 'video' else '图集',
                    'liked_count': note.get('likes', 0),
                    'collected_count': note.get('collects', 0),
                    'comment_count': note.get('comments', 0),
                    'share_count': note.get('shares', 0),
                    'upload_time': note.get('time', '')
                })
            
            self.save_note_history(session, notes_for_save)
            session.commit()
            
            # 6. 保存到Excel（可选）
            if all_new_comments:
                output_dir = 'output'
                os.makedirs(output_dir, exist_ok=True)
                
                # 保存评论
                comment_file = f'{output_dir}/{keyword}_{today}_comments.xlsx'
                save_to_xlsx(all_new_comments, comment_file, type='comment')
                logger.info(f"评论已保存到: {comment_file}")
            
            # 7. 发送邮件通知
            if self.email_notifier and all_new_comments:
                unique_users = len(set(c['user_id'] for c in all_new_comments))
                
                crawl_result = {
                    'keyword': keyword,
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'total_notes': len(all_notes),
                    'new_comments_count': len(all_new_comments),
                    'total_comments': total_comments,
                    'unique_users': unique_users,
                    'success': True,
                    'new_comments_list': all_new_comments
                }
                
                self.email_notifier.send_crawl_report(crawl_result)
            
            # 8. 更新任务日志
            crawl_log.status = 1
            crawl_log.end_time = datetime.now()
            crawl_log.total_notes = len(all_notes)
            crawl_log.total_comments = total_comments
            crawl_log.new_comments = len(all_new_comments)
            session.commit()
            
            logger.info(f"=== 采集完成 | 新增评论: {len(all_new_comments)} 条 ===")
            
            return all_notes, all_new_comments
            
        except Exception as e:
            session.rollback()
            crawl_log.status = 2
            crawl_log.end_time = datetime.now()
            crawl_log.error_msg = str(e)
            session.commit()
            logger.error(f"采集异常: {e}")
            raise
        finally:
            session.close()


def main():
    """主入口"""
    from config import DB_CONFIG, EMAIL_CONFIG
    
    # 初始化
    cookies_str, base_path = init()
    
    # 创建爬虫实例
    spider = IncrementalCommentSpider(
        db_url=DB_CONFIG['url'],
        email_config=EMAIL_CONFIG if EMAIL_CONFIG.get('sender_email') else None,
        use_mock_email=False  # 设为True使用模拟邮件（测试用）
    )
    
    # 执行采集
    keyword = CRAWL_CONFIG['keyword']
    max_pages = CRAWL_CONFIG['max_pages']
    
    logger.info(f"开始采集 | 关键词: {keyword} | 页数: {max_pages}")
    
    try:
        notes, comments = spider.run_incremental_crawl(
            keyword=keyword,
            max_pages=max_pages,
            cookies_str=cookies_str
        )
        logger.info(f"采集完成 | 笔记: {len(notes)} | 新增评论: {len(comments)}")
    except Exception as e:
        logger.error(f"采集失败: {e}")


if __name__ == '__main__':
    main()
