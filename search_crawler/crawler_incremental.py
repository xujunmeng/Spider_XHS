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

# ============================================
# ✅ 复用 1: 导入现有的API和数据处理工具
# ============================================
from apis.xhs_pc_apis import XHS_Apis
from xhs_utils.data_util import (
    handle_comment_info,    # ✅ 复用：评论数据处理
    save_to_xlsx,           # ✅ 复用：Excel保存
    timestamp_to_str        # ✅ 复用：时间戳转换
)
from xhs_utils.common_util import init

# 导入本包模块
from .config import CRAWL_CONFIG, DELAY_CONFIG
from .models import DatabaseManager, CommentHistory, NoteHistory, CrawlLog
from .cookie_pool_manager import CookiePoolManager
from .email_notifier import EmailNotifier, EmailNotifierMock
from .config import COOKIE_POOL


class IncrementalCommentSpider:
    """
    增量评论采集爬虫 - 复用现有代码版本
    
    本类按照技术方案文档第四章的要求，复用项目中已有的成熟逻辑：
    - 评论采集：复用 apis/xhs_pc_apis.py:get_note_all_comment()
    - 评论处理：复用 xhs_utils/data_util.py:handle_comment_info()
    - Excel保存：复用 xhs_utils/data_util.py:save_to_xlsx() + base_path
    - 时间转换：复用 xhs_utils/data_util.py:timestamp_to_str()
    """
    
    def __init__(self, db_url, base_path=None, email_config=None, use_mock_email=False, auto_sync_cookies=True):
        """
        :param db_url: 数据库连接URL
        :param base_path: 基础路径字典，由 init() 返回，格式为 {'media': ..., 'excel': ...}
        :param email_config: 邮件配置（可选）
        :param use_mock_email: 是否使用邮件模拟器（测试用）
        :param auto_sync_cookies: 是否自动同步 config.py 中的 Cookie 到数据库
        """
        # 注意：需先手动执行 SQL 初始化脚本创建表
        self.db_manager = DatabaseManager(db_url)
        self.cookie_manager = CookiePoolManager(self.db_manager)
        
        # ============================================
        # ✅ 复用：保存 base_path，用于后续Excel保存
        # ============================================
        self.base_path = base_path
        
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
        """
        生成评论唯一标识（用于去重）
        
        使用: note_id + comment_id + user_id + content(前50字) + 时间戳
        """
        note_id = comment.get('note_id', '')
        # API返回的是'id'，数据库字段是'comment_id'
        comment_id = comment.get('comment_id') or comment.get('id', '')
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
        """
        过滤出新增的评论（增量采集核心逻辑）
        
        :param session: 数据库会话
        :param comments: 采集到的所有评论列表（已由 handle_comment_info 处理）
        :return: 新增的评论列表
        """
        for comment in comments:
            comment['_unique_id'] = self.generate_comment_unique_id(comment)
        
        unique_ids = [c['_unique_id'] for c in comments]
        exists_set = self.batch_check_exists(session, unique_ids)
        
        new_comments = [c for c in comments if c['_unique_id'] not in exists_set]
        return new_comments
    
    def save_comment_history_batch(self, session, comments):
        """
        批量保存评论历史记录到MySQL
        
        注意：comment 字段已由 handle_comment_info() 标准化处理
        """
        if not comments:
            return 0
        
        comment_objects = []
        for comment in comments:
            # ✅ 字段已由 handle_comment_info() 标准化处理
            ch = CommentHistory(
                unique_id=comment.get('_unique_id'),
                note_id=comment.get('note_id'),
                comment_id=comment.get('comment_id'),  # ✅ handle_comment_info 已处理字段映射
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
                existing.upload_time = note.get('upload_time')
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
        """
        搜索笔记
        
        :param query: 搜索关键词
        :param page: 页码
        :param sort_type: 排序类型（1=最新优先）
        :param cookies_str: Cookie字符串
        :return: 笔记列表
        """
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
            
            # ============================================
            # 调试日志：打印第一条笔记的字段和数据结构
            # ============================================
            if notes and page == 1:  # 只在第一页打印，避免日志过多
                first_note = notes[0]
                note_card = first_note.get('note_card', {})
                user_info = note_card.get('user', {})
                logger.info("=" * 60)
                logger.info("【调试】搜索API返回的第一条笔记数据结构：")
                logger.info("=" * 60)
                logger.info(f"笔记字段列表: {list(first_note.keys())}")
                logger.info(f"笔记标题 (display_title): {note_card.get('display_title', '【无display_title】')}")
                logger.info(f"用户昵称 (nick_name): {user_info.get('nick_name', '【无nick_name】')}")
                logger.info(f"用户ID: {user_info.get('user_id', '【无user_id】')}")
                logger.info("=" * 60)
            
            return notes
            
        except Exception as e:
            logger.error(f"搜索笔记异常: {e}")
            return []
    
    # ============================================
    # ✅ 复用 2: 使用现有API和 handle_comment_info() 处理评论数据
    # ============================================
    def get_all_comments(self, note_url, cookies_str=''):
        """
        获取笔记的所有评论（复用现有API和数据处理）
        
        复用逻辑：
        1. 调用 apis/xhs_pc_apis.py 中的 get_note_all_comment() 获取原始数据
        2. 调用 xhs_utils/data_util.py 中的 handle_comment_info() 标准化处理
        
        :param note_url: 笔记URL
        :param cookies_str: Cookie字符串
        :return: 处理后的评论列表
        """
        try:
            # ✅ 复用：调用现有的 get_note_all_comment() API
            # 该方法内部已实现：
            # - 分页获取所有一级评论
            # - 遍历每条一级评论，分页获取所有二级回复
            success, msg, raw_comments = self.xhs_apis.get_note_all_comment(
                url=note_url,
                cookies_str=cookies_str
            )
            
            if not success:
                logger.error(f"获取评论失败: {msg}")
                return []
            
            if not raw_comments:
                return []
            
            # ✅ 复用：使用 handle_comment_info() 处理每条评论（包括一级和二级）
            processed_comments = []
            for comment in raw_comments:
                try:
                    # ============================================
                    # 处理一级评论
                    # ============================================
                    comment['note_url'] = note_url
                    processed = handle_comment_info(comment)
                    processed['parent_comment_id'] = ''
                    processed['comment_level'] = 1
                    processed['is_top'] = comment.get('is_top', False)  # 置顶标记
                    processed_comments.append(processed)
                    
                    # ============================================
                    # ✅ 修复：处理二级评论（sub_comments）
                    # ============================================
                    sub_comments = comment.get('sub_comments', [])
                    if sub_comments:
                        logger.debug(f"一级评论 {comment.get('id')} 有 {len(sub_comments)} 条二级评论")
                        for sub_comment in sub_comments:
                            try:
                                sub_comment['note_url'] = note_url
                                sub_processed = handle_comment_info(sub_comment)
                                
                                # 二级评论特有字段
                                sub_processed['parent_comment_id'] = comment.get('id')  # 父评论ID
                                sub_processed['comment_level'] = 2
                                sub_processed['reply_to_nickname'] = comment.get('user_info', {}).get('nickname', '')  # 回复给哪位用户
                                
                                processed_comments.append(sub_processed)
                            except Exception as sub_e:
                                logger.warning(f"处理二级评论数据失败: {sub_e}")
                                continue
                except Exception as e:
                    logger.warning(f"处理评论数据失败: {e}")
                    continue
            
            # 统计一级和二级评论数量
            level1_count = sum(1 for c in processed_comments if c['comment_level'] == 1)
            level2_count = sum(1 for c in processed_comments if c['comment_level'] == 2)
            logger.info(f"笔记评论处理完成: 一级 {level1_count} 条, 二级 {level2_count} 条, 总计 {len(processed_comments)} 条")
            return processed_comments
            
        except Exception as e:
            logger.error(f"获取评论异常: {e}")
            return []
    
    def _get_cookie_for_request(self, cookies_str=''):
        """获取用于请求的 Cookie，优先使用 CookiePoolManager"""
        # 如果传入了有效的 cookies_str，直接使用
        if cookies_str and len(cookies_str) > 10:
            return cookies_str
        
        # 否则从 CookiePoolManager 获取
        cookie_name, cookie_value = self.cookie_manager.get_available_cookie()
        if cookie_value:
            logger.info(f"使用 CookiePool 中的 cookie: {cookie_name}")
            return cookie_value
        
        logger.warning("没有可用的 Cookie，请检查配置")
        return ''
    
    def run_incremental_crawl(self, keyword=None, max_pages=None, cookies_str=''):
        """
        执行增量采集
        
        主流程：
        1. 分页搜索笔记
        2. 对每条笔记调用 get_all_comments()（复用现有API）
        3. 过滤新增评论（去重）
        4. 保存到MySQL和Excel
        
        :param keyword: 搜索关键词（默认使用配置）
        :param max_pages: 最大采集页数（默认使用配置）
        :param cookies_str: Cookie字符串（可选，不传则从 CookiePool 获取）
        :return: (笔记列表, 新增评论列表)
        """
        keyword = keyword or CRAWL_CONFIG['keyword']
        max_pages = max_pages or CRAWL_CONFIG['max_pages']
        
        # 获取 Cookie（优先使用传入的，否则从 CookiePool 获取）
        effective_cookies = self._get_cookie_for_request(cookies_str)
        
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
                
                notes = self.search_notes(keyword, page, CRAWL_CONFIG['sort_type'], effective_cookies)
                
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
                    comments = self.get_all_comments(note_url, effective_cookies)
                    total_comments += len(comments)
                    
                    logger.info(f"笔记 {note_id} 共有 {len(comments)} 条评论")
                    
                    # 3. 过滤新增评论
                    new_comments = self.filter_new_comments(session, comments)
                    
                    if new_comments:
                        # 关联笔记信息
                        # ============================================
                        # ✅ 修复：使用正确的字段路径
                        # 笔记数据在 note_card 下，标题是 display_title，用户是 user.nick_name
                        # ============================================
                        note_card = note.get('note_card', {})
                        user_info = note_card.get('user', {})
                        
                        # 获取笔记标题（display_title 可能为空）
                        note_title = note_card.get('display_title', '')
                        if not note_title:
                            note_title = '无标题'
                        
                        # 获取作者昵称（nick_name 或 nickname）
                        note_author = user_info.get('nick_name') or user_info.get('nickname', '未知作者')
                        note_author_id = user_info.get('user_id', '')
                        
                        # 获取笔记时间（从 corner_tag_info 或 time 字段）
                        corner_tag = note_card.get('corner_tag_info', [{}])[0] if note_card.get('corner_tag_info') else {}
                        note_time_display = corner_tag.get('text', '')  # 如 "5天前"
                        
                        for comment in new_comments:
                            comment['note_id'] = note_id
                            comment['note_url'] = note_url
                            comment['note_title'] = note_title
                            comment['note_author'] = note_author
                            comment['note_author_id'] = note_author_id
                            comment['note_upload_time'] = note_time_display
                            # 确保 comment_id 字段存在
                            if 'comment_id' not in comment and 'id' in comment:
                                comment['comment_id'] = comment['id']
                        
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
                # ============================================
                # ✅ 修复：使用正确的字段路径（note_card 下的字段）
                # ============================================
                note_card = note.get('note_card', {})
                user_info = note_card.get('user', {})
                interact_info = note_card.get('interact_info', {})
                
                # 获取笔记标题
                note_title = note_card.get('display_title', '')
                if not note_title:
                    note_title = '无标题'
                
                # 获取作者信息
                note_author = user_info.get('nick_name') or user_info.get('nickname', '未知作者')
                
                # 获取互动数据（转换为整数）
                liked_count = int(interact_info.get('liked_count', 0)) if interact_info.get('liked_count') else 0
                collected_count = int(interact_info.get('collected_count', 0)) if interact_info.get('collected_count') else 0
                comment_count = int(interact_info.get('comment_count', 0)) if interact_info.get('comment_count') else 0
                share_count = int(interact_info.get('shared_count', 0)) if interact_info.get('shared_count') else 0
                
                notes_for_save.append({
                    'note_id': note.get('id'),
                    'note_url': f"https://www.xiaohongshu.com/explore/{note.get('id')}",
                    'title': note_title,
                    'user_id': user_info.get('user_id', ''),
                    'nickname': note_author,
                    'note_type': '视频' if note_card.get('type') == 'video' else '图集',
                    'liked_count': liked_count,
                    'collected_count': collected_count,
                    'comment_count': comment_count,
                    'share_count': share_count,
                    'upload_time': None  # 搜索API返回的是相对时间，如"5天前"
                })
            
            self.save_note_history(session, notes_for_save)
            session.commit()
            
            # 6. 保存到Excel（可选）
            if all_new_comments:
                # ============================================
                # ✅ 复用：使用 base_path['excel'] 保存Excel
                # 与 main.py 中保存Excel的方式保持一致
                # ============================================
                excel_name = f'{keyword}_{today}_comments'
                file_path = os.path.abspath(os.path.join(self.base_path['excel'], f'{excel_name}.xlsx'))
                
                # ✅ 复用：使用现有的 save_to_xlsx() 保存评论
                save_to_xlsx(all_new_comments, file_path, type='comment')
                logger.info(f"评论已保存到: {file_path}")
            
            # 7. 发送邮件通知
            if self.email_notifier and all_new_comments:
                unique_users = len(set(c.get('user_id', '') for c in all_new_comments))
                
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
    
    # ============================================
    # ✅ 复用：调用 init() 获取 cookies_str 和 base_path
    # 与 main.py 中的使用方式保持一致
    # ============================================
    cookies_str, base_path = init()
    
    logger.info(f"Excel保存路径: {base_path['excel']}")
    
    # 创建爬虫实例
    spider = IncrementalCommentSpider(
        db_url=DB_CONFIG['url'],
        base_path=base_path,  # ✅ 复用：传入 base_path，用于Excel保存
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
