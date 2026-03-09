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
    'max_pages': 5,                     # 每次执行最多采集页数
    'sort_type': 1,                     # 1=最新优先
    'page_size': 20,                    # 每页数量
    'schedule_interval': 3600,          # 定时间隔(秒)，默认1小时
}

# 延迟配置（防反爬）
DELAY_CONFIG = {
    'page_interval': (3, 5),            # 页间延迟(秒)
    'note_interval': (3, 5),        # 笔记间延迟(秒)
    'comment_interval': (3, 5)      # 评论分页延迟(秒)
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
        'value': 'abRequestId=7e3310df-011a-5d42-943e-fb44df97212c; a1=19c94f738easkxvhhq9y1cv91oxe8lxj119x1sxe130000383551; webId=f769b9d526c8861d4325189df5578d03; gid=yjSj4iW4WdyYyjSj4iWqYyMCd0MTChxxAjvyjdyShjylCCq8dY1CVy888qYq22y88iDYY42j; xsecappid=xhs-pc-web; acw_tc=0a0bb2e117730675925137951e334a11084cfa518399ddbae8391804e9efae; webBuild=5.14.2; loadts=1773068533826; websectiga=634d3ad75ffb42a2ade2c5e1705a73c845837578aeb31ba0e442d75c648da36a; sec_poison_id=6029c34b-9e17-413f-a280-46fb5f470f5b; web_session=040069b81245c5fe2197fda99b3b4bef557358; id_token=VjEAAIb2I6VkpNgTmRkeho0aiBA/8ML/PpqCf1+LFddF6trnXnqS9MxkQ9if/40HiG2hzdRYwg5p1tq85AmCw5BJI+979EHCDMTN3g+XGJVcBPp8i2bxsMzBCnwQPZr9fJIlZpX3; unread={%22ub%22:%2269a951c0000000001a01dedd%22%2C%22ue%22:%2269ae5d0a000000001503bbee%22%2C%22uc%22:29}',  # 请填写实际Cookie值
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
