# ============================================
# 小红书爬虫配置文件
# ============================================

# 数据库配置（SQLAlchemy格式）
# 请根据实际情况修改数据库连接信息
DB_CONFIG = {
    'url': 'mysql+pymysql://root:12345678@localhost:3306/xhs_crawler?charset=utf8mb4',
    'pool_size': 5,
    'max_overflow': 10,
    'pool_recycle': 3600
}

# 爬虫配置
CRAWL_CONFIG = {
    'keyword': '51talk老带新',           # 搜索关键词
    'max_pages': 10,                     # 每次执行最多采集页数
    'sort_type': 1,                     # 1=最新优先
    'page_size': 20,                    # 每页数量
    'schedule_interval': 3600,          # 定时间隔(秒)，默认1小时
}

# 延迟配置（防反爬）
DELAY_CONFIG = {
    'page_interval': (1, 2),            # 页间延迟(秒)
    'note_interval': (0.5, 1.5),        # 笔记间延迟(秒)
    'comment_interval': (0.3, 0.8)      # 评论分页延迟(秒)
}

# Cookie池配置
COOKIE_POOL_CONFIG = {
    'max_fail_count': 5,                # 单Cookie最大失败次数
    'switch_strategy': 'round_robin'    # 切换策略: round_robin/random/least_used
}

# Cookie池列表（初始导入使用）
# 请从.env文件或安全位置读取实际Cookie值
COOKIE_POOL = [
    {
        'name': 'account_01',
        'value': '',  # 请填写实际Cookie值
        'account_info': '主账号'
    },
    # {
    #     'name': 'account_02',
    #     'value': '',  # 备用账号
    #     'account_info': '备用账号1'
    # },
]

# 邮件通知配置（QQ邮箱示例）
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'smtp_port': 465,
    'sender_email': 'your_qq@qq.com',       # 发件人QQ邮箱
    'sender_password': 'your_auth_code',     # 16位授权码（非登录密码）
    'receiver_email': 'target_qq@qq.com'     # 收件人QQ邮箱
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}',
    'file': 'logs/crawler.log',
    'rotation': '10 MB'
}
