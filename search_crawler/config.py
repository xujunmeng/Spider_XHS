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
    'max_pages': 3,                     # 每次执行最多采集页数
    'sort_type': 1,                     # 1=最新优先
    'page_size': 20,                    # 每页数量
    
    # 定时调度配置（统一在此配置）
    'schedule_interval': 600,          # 定时间隔(秒)，默认1小时=3600秒
    'schedule_cron': '0',               # Cron表达式（分钟位），默认每小时的第0分钟执行
    
    # APScheduler 容错配置（统一从CRAWL_CONFIG读取）
    'misfire_grace_time': 3600,         # 任务错过执行时间后，多少秒内仍可补执行（默认1小时）
    'coalesce': True,                   # 合并错过的多次任务，只执行一次（避免堆积）
    'max_instances': 1,                 # 同一时间只允许一个任务实例运行（防止并发冲突）
    'thread_pool_workers': 10,          # 线程池工作线程数
}

# 延迟配置（防反爬）
DELAY_CONFIG = {
    'page_interval': (2, 4),            # 页间延迟(秒)
    'note_interval': (2, 4),        # 笔记间延迟(秒)
    'comment_interval': (2, 4)      # 评论分页延迟(秒)
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
        'value': 'abRequestId=7e3310df-011a-5d42-943e-fb44df97212c; a1=19c94f738easkxvhhq9y1cv91oxe8lxj119x1sxe130000383551; webId=f769b9d526c8861d4325189df5578d03; gid=yjSj4iW4WdyYyjSj4iWqYyMCd0MTChxxAjvyjdyShjylCCq8dY1CVy888qYq22y88iDYY42j; unread={%22ub%22:%2269a951c0000000001a01dedd%22%2C%22ue%22:%2269ae5d0a000000001503bbee%22%2C%22uc%22:29}; webBuild=5.14.6; acw_tc=0a4aafd317732344948006520e8fa20695bdd0640fe349b73f7e05e9654e52; web_session=040069b81245c5fe21971021843b4bb4935648; id_token=VjEAAASQ9/j9PmY8hj9J0kRr1jE6QT0jbJ2EJBXMOG3SXzzUulDE2/ikIWYWXK7Il4BDESJWhztwd59iyuUwerj/WmkmqtaDv504ZRxuaFDY7YQUU1tJfNqSZEqhabqZNlNAKlMc; xsecappid=fe-login; loadts=1773234557651; websectiga=8886be45f388a1ee7bf611a69f3e174cae48f1ea02c0f8ec3256031b8be9c7ee; sec_poison_id=b0a9c277-fc6c-4e7c-a425-2e77bb0d7b72}',  # 请填写实际Cookie值
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
    'sender_email': '448725919@qq.com',       # 发件人QQ邮箱
    'sender_password': 'jqemsjyfmfaabijb',     # 16位授权码（非登录密码）
    'receiver_email': '448725919@qq.com'     # 收件人QQ邮箱
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}',
    'file': 'logs/crawler.log',
    'rotation': '10 MB'
}
