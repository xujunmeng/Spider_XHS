# 阿里云 ECS 部署指南

## 服务器配置建议

### 最低配置（可运行）
- **CPU**: 2核
- **内存**: 2GB
- **系统盘**: 40GB SSD
- **带宽**: 1Mbps（足够，爬虫主要是下行流量）
- **数据库**: MySQL建议使用阿里云RDS（不在ECS上跑DB）

### 推荐配置（舒适运行）
- **CPU**: 2核
- **内存**: 4GB  ← 更稳妥
- **系统盘**: 40GB SSD
- **数据库**: 阿里云RDS MySQL基础版

---

## 2C2G 优化配置

### 1. 系统级优化

```bash
# 创建 swap 分区（内存不足时使用）
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2. Python 内存优化

编辑 `search_crawler/crawler_incremental.py`，限制批量处理大小：

```python
# 在 __init__ 中添加
self.batch_size = 100  # 每批处理100条评论，避免内存暴涨
```

### 3. 使用 Systemd 管理（守护进程）

创建服务文件 `/etc/systemd/system/xhs-crawler.service`：

```ini
[Unit]
Description=Xiaohongshu Crawler Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/Spider_XHS
Environment="PYTHONPATH=/home/your-user/Spider_XHS"
Environment="ENV=production"

# 内存限制（2G机器建议限制1.5G）
MemoryMax=1536M
MemorySwapMax=512M

# 自动重启
Restart=always
RestartSec=10

# 启动命令
ExecStart=/home/your-user/Spider_XHS/.venv/bin/python -m search_crawler.scheduler

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable xhs-crawler
sudo systemctl start xhs-crawler

# 查看状态
sudo systemctl status xhs-crawler
sudo journalctl -u xhs-crawler -f
```

### 4. 日志切割（避免磁盘占满）

创建 `/etc/logrotate.d/xhs-crawler`：

```
/home/your-user/Spider_XHS/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 your-user your-user
}
```

---

## 监控建议

### 1. 基础监控命令

```bash
# 实时查看内存使用
free -h

# 查看Python进程内存
top -p $(pgrep -d',' -f 'scheduler.py')

# 查看磁盘空间
df -h
```

### 2. 阿里云云监控

建议配置告警：
- **内存使用率** > 80% 告警
- **CPU使用率** > 90% 告警（持续5分钟）
- **磁盘使用率** > 80% 告警

---

## 常见问题

### Q: 爬虫运行一段时间后内存占用越来越高？

这是Python的内存碎片问题，解决方案：

1. 每晚自动重启服务：
```bash
# crontab -e
0 3 * * * sudo systemctl restart xhs-crawler
```

2. 或在代码中添加定期强制gc：
```python
import gc
# 在每次采集完成后
gc.collect()
```

### Q: 爬虫被小红书封IP？

- 阿里云ECS的IP容易被识别为服务器IP
- 建议使用代理IP池（在 `cookie_pool_manager.py` 中配置）
- 或者降低采集频率（改为每2小时一次）

---

## 总结

| 场景 | 2C2G是否足够 |
|------|-------------|
| 测试/小规模采集 | ✅ 足够 |
| 生产环境，关键词少 | ✅ 可以，需优化 |
| 生产环境，大数据量 | ❌ 建议4G内存 |
| 数据库也在本机 | ❌ 绝对不够 |

**建议生产环境使用 2C4G + RDS**，成本增加不多但稳定性更好。
