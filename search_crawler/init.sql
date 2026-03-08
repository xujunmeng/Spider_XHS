-- ============================================
-- 小红书爬虫数据库初始化脚本
-- 数据库: xhs_crawler
-- 字符集: utf8mb4
-- ============================================

-- 创建数据库（如不存在）
CREATE DATABASE IF NOT EXISTS xhs_crawler 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE xhs_crawler;

-- ============================================
-- 1. 评论历史记录表
-- ============================================
CREATE TABLE IF NOT EXISTS comment_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
    unique_id VARCHAR(32) NOT NULL COMMENT '评论唯一标识(MD5)',
    note_id VARCHAR(64) NOT NULL COMMENT '笔记ID',
    comment_id VARCHAR(64) NOT NULL COMMENT '评论ID',
    parent_comment_id VARCHAR(64) DEFAULT NULL COMMENT '父评论ID（一级评论为空）',
    user_id VARCHAR(64) DEFAULT NULL COMMENT '用户ID',
    nickname VARCHAR(128) DEFAULT NULL COMMENT '用户昵称',
    content TEXT COMMENT '评论内容',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    upload_time DATETIME DEFAULT NULL COMMENT '评论发布时间',
    ip_location VARCHAR(64) DEFAULT NULL COMMENT 'IP归属地',
    first_seen_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '首次发现时间',
    last_check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后检查时间',
    
    UNIQUE KEY uk_unique_id (unique_id),
    KEY idx_note_id (note_id),
    KEY idx_comment_id (comment_id),
    KEY idx_user_id (user_id),
    KEY idx_upload_time (upload_time),
    KEY idx_first_seen (first_seen_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论历史记录表';

-- ============================================
-- 2. 笔记历史记录表
-- ============================================
CREATE TABLE IF NOT EXISTS note_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
    note_id VARCHAR(64) NOT NULL COMMENT '笔记ID',
    note_url VARCHAR(512) DEFAULT NULL COMMENT '笔记链接',
    title VARCHAR(512) DEFAULT NULL COMMENT '笔记标题',
    user_id VARCHAR(64) DEFAULT NULL COMMENT '作者用户ID',
    nickname VARCHAR(128) DEFAULT NULL COMMENT '作者昵称',
    note_type VARCHAR(32) DEFAULT NULL COMMENT '笔记类型：图集/视频',
    liked_count INT DEFAULT 0 COMMENT '点赞数',
    collected_count INT DEFAULT 0 COMMENT '收藏数',
    comment_count INT DEFAULT 0 COMMENT '评论数',
    share_count INT DEFAULT 0 COMMENT '分享数',
    upload_time DATETIME DEFAULT NULL COMMENT '笔记发布时间',
    first_crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '首次采集时间',
    last_crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后采集时间',
    
    UNIQUE KEY uk_note_id (note_id),
    KEY idx_user_id (user_id),
    KEY idx_upload_time (upload_time),
    KEY idx_last_crawl (last_crawl_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='笔记历史记录表';

-- ============================================
-- 3. 采集任务日志表
-- ============================================
CREATE TABLE IF NOT EXISTS crawl_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    keyword VARCHAR(256) DEFAULT NULL COMMENT '搜索关键词',
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '任务开始时间',
    end_time TIMESTAMP NULL DEFAULT NULL COMMENT '任务结束时间',
    status TINYINT DEFAULT 0 COMMENT '任务状态：0-运行中 1-成功 2-失败',
    total_notes INT DEFAULT 0 COMMENT '采集笔记总数',
    total_comments INT DEFAULT 0 COMMENT '采集评论总数',
    new_comments INT DEFAULT 0 COMMENT '新增评论数',
    error_msg TEXT COMMENT '错误信息',
    
    KEY idx_task_id (task_id),
    KEY idx_start_time (start_time),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集任务日志表';

-- ============================================
-- 4. Cookie池管理表
-- ============================================
CREATE TABLE IF NOT EXISTS cookie_pool (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
    cookie_name VARCHAR(64) NOT NULL COMMENT 'Cookie标识名称',
    cookie_value TEXT NOT NULL COMMENT 'Cookie字符串',
    account_info VARCHAR(256) DEFAULT NULL COMMENT '账号信息(备注)',
    status TINYINT DEFAULT 1 COMMENT '状态：0-失效 1-正常 2-冻结',
    use_count INT DEFAULT 0 COMMENT '使用次数',
    success_count INT DEFAULT 0 COMMENT '成功请求次数',
    fail_count INT DEFAULT 0 COMMENT '失败请求次数',
    last_used_time TIMESTAMP NULL DEFAULT NULL COMMENT '最后使用时间',
    last_success_time TIMESTAMP NULL DEFAULT NULL COMMENT '最后成功时间',
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    UNIQUE KEY uk_cookie_name (cookie_name),
    KEY idx_status (status),
    KEY idx_last_used (last_used_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Cookie池管理表';

-- ============================================
-- 5. Cookie使用日志表
-- ============================================
CREATE TABLE IF NOT EXISTS cookie_usage_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
    cookie_name VARCHAR(64) NOT NULL COMMENT '使用的Cookie',
    task_id VARCHAR(64) DEFAULT NULL COMMENT '任务ID',
    request_url VARCHAR(512) DEFAULT NULL COMMENT '请求URL',
    response_status INT DEFAULT NULL COMMENT '响应状态码',
    is_success TINYINT DEFAULT 0 COMMENT '是否成功：0-失败 1-成功',
    error_msg TEXT COMMENT '错误信息',
    use_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '使用时间',
    
    KEY idx_cookie_name (cookie_name),
    KEY idx_task_id (task_id),
    KEY idx_use_time (use_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Cookie使用日志表';
