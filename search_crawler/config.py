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
    'max_pages': 1,                     # 每次执行最多采集页数
    'sort_type': 1,                     # 1=最新优先
    'page_size': 20,                    # 每页数量
    'schedule_interval': 3600,          # 定时间隔(秒)，默认1小时
}

# 延迟配置（防反爬）
DELAY_CONFIG = {
    'page_interval': (10, 20),            # 页间延迟(秒)
    'note_interval': (20, 30),        # 笔记间延迟(秒)
    'comment_interval': (10, 30)      # 评论分页延迟(秒)
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
        'value': 'abRequestId=7e3310df-011a-5d42-943e-fb44df97212c; a1=19c94f738easkxvhhq9y1cv91oxe8lxj119x1sxe130000383551; webId=f769b9d526c8861d4325189df5578d03; gid=yjSj4iW4WdyYyjSj4iWqYyMCd0MTChxxAjvyjdyShjylCCq8dY1CVy888qYq22y88iDYY42j; webBuild=5.14.0; xsecappid=xhs-pc-web; acw_tc=0a0b14e217729805534593089e62368c57395c7eb892aa5b00da7c72b267a0; web_session=040069b5eb3bd0f905a224c6983b4b1e1b0702; id_token=VjEAACzddrembl6djDi9eotQPERmyp4DS1gRTbN6S0uJaHg6IJx4lchCxxmJYm4m37upyDoYOBGioCB3CLkXk22s1hdd0NEs66OG1rG8Okg2TPpjdbU7535isvjmkKrihe16pY9s; loadts=1772982152157; unread={%22ub%22:%226996e82e000000001d0113ff%22%2C%22ue%22:%2269aa8962000000002602cdb4%22%2C%22uc%22:13}; websectiga=634d3ad75ffb42a2ade2c5e1705a73c845837578aeb31ba0e442d75c648da36a; sec_poison_id=3582f653-28a0-4c9d-859b-59137b50693d',  # 请填写实际Cookie值
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
