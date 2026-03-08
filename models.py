# ============================================
# SQLAlchemy ORM 模型定义
# ============================================

from sqlalchemy import create_engine, Column, BigInteger, Integer, String, Text, DateTime, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class CommentHistory(Base):
    """评论历史记录表"""
    __tablename__ = 'comment_history'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    unique_id = Column(String(32), unique=True, nullable=False, comment='评论唯一标识(MD5)')
    note_id = Column(String(64), nullable=False, comment='笔记ID', index=True)
    comment_id = Column(String(64), nullable=False, comment='评论ID', index=True)
    parent_comment_id = Column(String(64), nullable=True, comment='父评论ID（一级评论为空）')
    user_id = Column(String(64), nullable=True, comment='用户ID', index=True)
    nickname = Column(String(128), nullable=True, comment='用户昵称')
    content = Column(Text, nullable=True, comment='评论内容')
    like_count = Column(Integer, default=0, comment='点赞数')
    upload_time = Column(DateTime, nullable=True, comment='评论发布时间', index=True)
    ip_location = Column(String(64), nullable=True, comment='IP归属地')
    first_seen_time = Column(TIMESTAMP, default=datetime.now, comment='首次发现时间')
    last_check_time = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment='最后检查时间')


class NoteHistory(Base):
    """笔记历史记录表"""
    __tablename__ = 'note_history'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    note_id = Column(String(64), unique=True, nullable=False, comment='笔记ID')
    note_url = Column(String(512), nullable=True, comment='笔记链接')
    title = Column(String(512), nullable=True, comment='笔记标题')
    user_id = Column(String(64), nullable=True, comment='作者用户ID', index=True)
    nickname = Column(String(128), nullable=True, comment='作者昵称')
    note_type = Column(String(32), nullable=True, comment='笔记类型：图集/视频')
    liked_count = Column(Integer, default=0, comment='点赞数')
    collected_count = Column(Integer, default=0, comment='收藏数')
    comment_count = Column(Integer, default=0, comment='评论数')
    share_count = Column(Integer, default=0, comment='分享数')
    upload_time = Column(DateTime, nullable=True, comment='笔记发布时间', index=True)
    first_crawl_time = Column(TIMESTAMP, default=datetime.now, comment='首次采集时间')
    last_crawl_time = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now, comment='最后采集时间')


class CrawlLog(Base):
    """采集任务日志表"""
    __tablename__ = 'crawl_log'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    task_id = Column(String(64), nullable=False, comment='任务ID', index=True)
    keyword = Column(String(256), nullable=True, comment='搜索关键词')
    start_time = Column(TIMESTAMP, default=datetime.now, comment='任务开始时间', index=True)
    end_time = Column(DateTime, nullable=True, comment='任务结束时间')
    status = Column(Integer, default=0, comment='任务状态：0-运行中 1-成功 2-失败')
    total_notes = Column(Integer, default=0, comment='采集笔记总数')
    total_comments = Column(Integer, default=0, comment='采集评论总数')
    new_comments = Column(Integer, default=0, comment='新增评论数')
    error_msg = Column(Text, nullable=True, comment='错误信息')


class CookiePool(Base):
    """Cookie池管理表"""
    __tablename__ = 'cookie_pool'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增ID')
    cookie_name = Column(String(64), unique=True, nullable=False, comment='Cookie标识名称')
    cookie_value = Column(Text, nullable=False, comment='Cookie字符串')
    account_info = Column(String(256), nullable=True, comment='账号信息(备注)')
    status = Column(Integer, default=1, comment='状态：0-失效 1-正常 2-冻结')
    use_count = Column(Integer, default=0, comment='使用次数')
    success_count = Column(Integer, default=0, comment='成功请求次数')
    fail_count = Column(Integer, default=0, comment='失败请求次数')
    last_used_time = Column(DateTime, nullable=True, comment='最后使用时间', index=True)
    last_success_time = Column(DateTime, nullable=True, comment='最后成功时间')
    created_time = Column(TIMESTAMP, default=datetime.now, comment='创建时间')


class CookieUsageLog(Base):
    """Cookie使用日志表"""
    __tablename__ = 'cookie_usage_log'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增ID')
    cookie_name = Column(String(64), nullable=False, comment='使用的Cookie', index=True)
    task_id = Column(String(64), nullable=True, comment='任务ID', index=True)
    request_url = Column(String(512), nullable=True, comment='请求URL')
    response_status = Column(Integer, nullable=True, comment='响应状态码')
    is_success = Column(Integer, default=0, comment='是否成功：0-失败 1-成功')
    error_msg = Column(Text, nullable=True, comment='错误信息')
    use_time = Column(TIMESTAMP, default=datetime.now, comment='使用时间', index=True)


# 数据库连接管理
class DatabaseManager:
    """数据库连接管理器"""
    
    def __init__(self, db_url):
        """
        :param db_url: 数据库连接URL
        格式: mysql+pymysql://user:password@host:port/database?charset=utf8mb4
        """
        self.engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """获取数据库会话"""
        return self.Session()
    
    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()
