# ============================================
# 邮件通知器 - 支持QQ邮箱/企业邮箱等
# ============================================

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from datetime import datetime
from loguru import logger
from collections import defaultdict


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, smtp_config):
        """
        :param smtp_config: SMTP配置字典
        {
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 465,
            'sender_email': 'your_qq@qq.com',
            'sender_password': 'authorization_code',
            'receiver_email': 'target@qq.com'
        }
        """
        self.smtp_config = smtp_config
    
    def send_crawl_report(self, crawl_result):
        """
        发送采集报告邮件
        :param crawl_result: 采集结果字典
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['sender_email']
            msg['To'] = self.smtp_config['receiver_email']
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = self._build_subject(crawl_result)
            
            html_body = self._build_html_body(crawl_result)
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            server = smtplib.SMTP_SSL(
                self.smtp_config['smtp_server'],
                self.smtp_config['smtp_port']
            )
            server.login(
                self.smtp_config['sender_email'],
                self.smtp_config['sender_password']
            )
            server.sendmail(
                self.smtp_config['sender_email'],
                self.smtp_config['receiver_email'],
                msg.as_string()
            )
            server.quit()
            
            logger.info(f"邮件发送成功: {self.smtp_config['receiver_email']}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def _build_subject(self, result):
        """构建邮件主题"""
        keyword = result.get('keyword', '51talk老带新')
        crawl_time = result.get('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M'))
        new_count = result.get('new_comments_count', 0)
        status = '成功' if result.get('success') else '失败'
        
        return f"【小红书爬虫】{keyword} - {crawl_time} 采集报告 | 新增评论{new_count}条 | {status}"
    
    def _build_html_body(self, result):
        """构建HTML邮件正文"""
        keyword = result.get('keyword', '51talk老带新')
        crawl_time = result.get('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M'))
        total_notes = result.get('total_notes', 0)
        new_comments = result.get('new_comments_count', 0)
        total_comments = result.get('total_comments', 0)
        unique_users = result.get('unique_users', 0)
        status = result.get('success', True)
        comments_list = result.get('new_comments_list', [])
        
        status_html = '<span style="color: green;">✅ 成功</span>' if status else '<span style="color: red;">❌ 失败</span>'
        
        # 按笔记ID分组构建评论列表HTML
        comments_by_note = defaultdict(list)
        for comment in comments_list:
            note_id = comment.get('note_id', 'unknown')
            comments_by_note[note_id].append(comment)
        
        comments_html = ''
        
        for note_id, note_comments in comments_by_note.items():
            if not note_comments:
                continue
            
            # 获取笔记信息
            first_comment = note_comments[0]
            note_url = first_comment.get('note_url', f'https://www.xiaohongshu.com/explore/{note_id}')
            note_title = first_comment.get('note_title', f'笔记 {note_id}')
            note_author = first_comment.get('note_author', '未知作者')
            note_time = first_comment.get('note_upload_time', '')
            
            # 分离一级和二级评论
            level1_comments = [c for c in note_comments if c.get('comment_level') == 1]
            level2_comments = [c for c in note_comments if c.get('comment_level') == 2]
            
            comments_html += f"""
            <div style="margin: 20px 0; border: 1px solid #ffe4e4; border-radius: 8px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #ff2442, #ff5c7c); color: white; padding: 12px 15px;">
                    <div style="font-size: 16px; font-weight: bold;">📄 {note_title[:60]}{'...' if len(note_title) > 60 else ''}</div>
                    <div style="font-size: 13px; margin-top: 6px; opacity: 0.95;">
                        <span>👤 作者：@{note_author}</span>
                        {f'<span style="margin-left: 20px;">🕐 笔记时间：{note_time}</span>' if note_time else ''}
                        <a href="{note_url}" style="color: #fff; text-decoration: underline; margin-left: 20px;">查看笔记 →</a>
                    </div>
                </div>
                <div style="padding: 15px; background: #fff;">
            """
            
            # 收集所有已展示的一级评论ID（用于识别"孤立"的二级评论）
            displayed_level1_ids = set()
            
            # 按一级评论组织展示
            for comment in level1_comments:
                comments_html += self._render_level1_comment(comment, level2_comments)
                displayed_level1_ids.add(comment.get('comment_id') or comment.get('id', ''))
            
            # 处理"孤立"的二级评论（其父评论不在新增列表中）
            orphan_level2 = [c for c in level2_comments if c.get('parent_comment_id') not in displayed_level1_ids]
            if orphan_level2:
                comments_html += """
                    <div style="margin: 15px 0; padding: 10px; background: #fff8e1; border-left: 4px solid #ffc107; border-radius: 4px;">
                        <div style="color: #f57c00; font-size: 13px; font-weight: bold; margin-bottom: 8px;">
                            💬 以下是对已有评论的新回复
                        </div>
                """
                for sub in orphan_level2:
                    comments_html += self._render_orphan_level2_comment(sub)
                comments_html += "</div>"
            
            # 显示统计信息
            level1_count = len(level1_comments)
            level2_count = len(level2_comments)
            total_count = level1_count + level2_count
            
            comments_html += f"""
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #f0f0f0; color: #666; font-size: 12px;">
                        该笔记共 <strong>{total_count}</strong> 条新增评论（一级 <strong>{level1_count}</strong> 条，二级 <strong>{level2_count}</strong> 条）
                    </div>
                </div>
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #ff2442, #ff5c7c); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .stats {{ background: #f8f9fa; padding: 20px; margin: 15px 0; border-left: 4px solid #ff2442; border-radius: 4px; }}
                .stats ul {{ list-style: none; padding: 0; margin: 0; }}
                .stats li {{ padding: 8px 0; border-bottom: 1px dashed #ddd; }}
                .stats li:last-child {{ border-bottom: none; }}
                .stats strong {{ color: #ff2442; font-size: 18px; }}
                .comment-list {{ margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 2px solid #eee; color: #666; font-size: 12px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🕷️ 小红书爬虫采集报告</h2>
                <p>关键词：<strong>{keyword}</strong> | 采集时间：{crawl_time}</p>
            </div>
            
            <div class="stats">
                <h3>📊 采集统计</h3>
                <ul>
                    <li>📄 采集笔记数：<strong>{total_notes}</strong> 篇</li>
                    <li>💬 新增评论数：<strong>{new_comments}</strong> 条（共采集 {total_comments} 条）</li>
                    <li>👤 涉及用户数：<strong>{unique_users}</strong> 人</li>
                    <li>📌 任务状态：{status_html}</li>
                </ul>
            </div>
            
            <h3>💬 新增评论详情（共 {new_comments} 条）</h3>
            <div class="comment-list">
                {comments_html}
            </div>
            
            <div class="footer">
                <p>此邮件由小红书爬虫系统自动发送 | 发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _render_level1_comment(self, comment, all_level2):
        """渲染一级评论及其二级评论，返回HTML字符串"""
        nickname = comment.get('nickname', '未知用户')
        upload_time = comment.get('upload_time', '')
        ip_location = comment.get('ip_location', '未知')
        content = comment.get('content', '')
        like_count = comment.get('like_count', 0)
        show_tags = comment.get('show_tags', '')
        home_url = comment.get('home_url', '')
        avatar = comment.get('avatar', '')
        is_top = comment.get('is_top', False)
        comment_id = comment.get('comment_id') or comment.get('id', '')
        
        top_badge = '<span style="background: #ff2442; color: white; font-size: 10px; padding: 2px 6px; border-radius: 3px; margin-left: 8px;">置顶</span>' if is_top else ''
        tags_html = f'<span style="color: #999; font-size: 12px;">🏷️ {show_tags}</span>' if show_tags else ''
        avatar_html = f'<img src="{avatar}" style="width: 32px; height: 32px; border-radius: 50%; margin-right: 8px;" />' if avatar else ''
        
        if home_url:
            nickname_html = f'<a href="{home_url}" style="color: #ff2442; font-weight: bold; font-size: 14px; text-decoration: none;">👤 @{nickname}</a>'
        else:
            nickname_html = f'<span style="color: #ff2442; font-weight: bold; font-size: 14px;">👤 @{nickname}</span>'
        
        # 渲染二级评论
        sub_comments_html = ''
        related_level2 = [c for c in all_level2 if c.get('parent_comment_id') == comment_id]
        if related_level2:
            sub_comments_html = '<div style="margin-top: 8px; margin-left: 20px; padding-left: 15px; border-left: 3px solid #e0e0e0;">'
            for j, sub in enumerate(related_level2, 1):
                sub_comments_html += self._render_level2_comment(sub, j == len(related_level2))
            sub_comments_html += '</div>'
        
        # 一级评论HTML
        return f"""
            <div style="border-bottom: 1px dashed #eee; padding: 12px 0;">
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 8px;">
                    {avatar_html}
                    {nickname_html}
                    {top_badge}
                    <span style="color: #666; font-size: 12px;">🕐 {upload_time}</span>
                    <span style="color: #999; font-size: 12px;">📍 {ip_location}</span>
                    <span style="color: #ff2442; font-size: 12px;">❤️ {like_count}</span>
                    {tags_html}
                    <span style="background: #e3f2fd; color: #1976d2; font-size: 10px; padding: 2px 6px; border-radius: 3px;">一级评论</span>
                </div>
                <p style="margin: 0; padding: 10px; background: #f9f9f9; border-radius: 4px; line-height: 1.6; font-weight: 500;">
                    {content}
                </p>
                {sub_comments_html}
            </div>
        """
    
    def _render_level2_comment(self, sub_comment, is_last):
        """渲染单个二级评论"""
        nickname = sub_comment.get('nickname', '未知用户')
        upload_time = sub_comment.get('upload_time', '')
        ip_location = sub_comment.get('ip_location', '未知')
        content = sub_comment.get('content', '')
        like_count = sub_comment.get('like_count', 0)
        show_tags = sub_comment.get('show_tags', '')
        home_url = sub_comment.get('home_url', '')
        avatar = sub_comment.get('avatar', '')
        reply_to = sub_comment.get('reply_to_nickname', '')
        
        tags_html = f'<span style="color: #999; font-size: 11px;">🏷️ {show_tags}</span>' if show_tags else ''
        avatar_html = f'<img src="{avatar}" style="width: 24px; height: 24px; border-radius: 50%; margin-right: 6px;" />' if avatar else ''
        reply_hint = f'<span style="color: #666; font-size: 11px;">↩️ 回复 @{reply_to}</span>' if reply_to else ''
        
        if home_url:
            nickname_html = f'<a href="{home_url}" style="color: #ff2442; font-weight: bold; font-size: 13px; text-decoration: none;">@{nickname}</a>'
        else:
            nickname_html = f'<span style="color: #ff2442; font-weight: bold; font-size: 13px;">@{nickname}</span>'
        
        border_style = '' if is_last else 'border-bottom: 1px dotted #f0f0f0;'
        
        return f"""
            <div style="padding: 8px 0; {border_style}">
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 4px;">
                    {avatar_html}
                    {nickname_html}
                    {reply_hint}
                    <span style="color: #888; font-size: 11px;">🕐 {upload_time}</span>
                    <span style="color: #aaa; font-size: 11px;">📍 {ip_location}</span>
                    <span style="color: #ff2442; font-size: 11px;">❤️ {like_count}</span>
                    {tags_html}
                    <span style="background: #fff3e0; color: #f57c00; font-size: 9px; padding: 1px 4px; border-radius: 2px;">二级评论</span>
                </div>
                <p style="margin: 0; padding: 8px; background: #fafafa; border-radius: 3px; line-height: 1.5; font-size: 13px; color: #555;">
                    {content}
                </p>
            </div>
        """
    
    def _render_orphan_level2_comment(self, sub_comment):
        """渲染"孤立"的二级评论（其父评论不在新增列表中）"""
        nickname = sub_comment.get('nickname', '未知用户')
        upload_time = sub_comment.get('upload_time', '')
        ip_location = sub_comment.get('ip_location', '未知')
        content = sub_comment.get('content', '')
        like_count = sub_comment.get('like_count', 0)
        show_tags = sub_comment.get('show_tags', '')
        home_url = sub_comment.get('home_url', '')
        avatar = sub_comment.get('avatar', '')
        reply_to = sub_comment.get('reply_to_nickname', '')
        
        tags_html = f'<span style="color: #999; font-size: 11px;">🏷️ {show_tags}</span>' if show_tags else ''
        avatar_html = f'<img src="{avatar}" style="width: 24px; height: 24px; border-radius: 50%; margin-right: 6px;" />' if avatar else ''
        reply_hint = f'<span style="color: #666; font-size: 11px;">↩️ 回复 @{reply_to}</span>' if reply_to else ''
        
        if home_url:
            nickname_html = f'<a href="{home_url}" style="color: #ff2442; font-weight: bold; font-size: 13px; text-decoration: none;">@{nickname}</a>'
        else:
            nickname_html = f'<span style="color: #ff2442; font-weight: bold; font-size: 13px;">@{nickname}</span>'
        
        return f"""
            <div style="padding: 6px 0; border-bottom: 1px dotted #ffe0b2;">
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 3px;">
                    {avatar_html}
                    {nickname_html}
                    {reply_hint}
                    <span style="color: #888; font-size: 11px;">🕐 {upload_time}</span>
                    <span style="color: #aaa; font-size: 11px;">📍 {ip_location}</span>
                    <span style="color: #ff2442; font-size: 11px;">❤️ {like_count}</span>
                    {tags_html}
                    <span style="background: #fff3e0; color: #f57c00; font-size: 9px; padding: 1px 4px; border-radius: 2px;">新回复</span>
                </div>
                <p style="margin: 0; padding: 6px 8px; background: #fff; border-radius: 3px; line-height: 1.5; font-size: 13px; color: #555;">
                    {content}
                </p>
            </div>
        """


class EmailNotifierMock:
    """邮件通知模拟器（测试用，不实际发送邮件）"""
    
    def __init__(self, smtp_config):
        self.smtp_config = smtp_config
    
    def send_crawl_report(self, crawl_result):
        """模拟发送，仅记录日志"""
        logger.info("[MOCK] 邮件发送模拟")
        logger.info(f"[MOCK] 收件人: {self.smtp_config['receiver_email']}")
        logger.info(f"[MOCK] 主题: {crawl_result.get('keyword', '')}")
        logger.info(f"[MOCK] 新增评论数: {crawl_result.get('new_comments_count', 0)}")
        # 统计一级和二级评论
        comments_list = crawl_result.get('new_comments_list', [])
        level1 = sum(1 for c in comments_list if c.get('comment_level') == 1)
        level2 = sum(1 for c in comments_list if c.get('comment_level') == 2)
        logger.info(f"[MOCK] 一级评论: {level1} 条, 二级评论: {level2} 条")
        return True
