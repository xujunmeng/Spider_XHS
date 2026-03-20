#!/bin/bash
# ============================================
# 小红书爬虫一键启动脚本
# ============================================

# 设置项目路径
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
CRAWLER_LOG="$LOG_DIR/crawler.log"
PID_FILE="$PROJECT_DIR/crawler.pid"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 激活虚拟环境
source "$PROJECT_DIR/.venv/bin/activate"

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️ 爬虫已在运行 (PID: $PID)"
        echo "查看日志: tail -f $CRAWLER_LOG"
        exit 1
    else
        rm "$PID_FILE"
    fi
fi

echo "🚀 启动小红书爬虫..."
echo "项目路径: $PROJECT_DIR"
echo ""
echo "日志文件: $CRAWLER_LOG"
echo ""

# 后台启动（标准输出也追加到 crawler.log，与业务日志统一）
nohup python3 -m search_crawler.scheduler >> "$CRAWLER_LOG" 2>&1 &

# 保存 PID
PID=$!
echo $PID > "$PID_FILE"

echo "✅ 爬虫已启动 (PID: $PID)"
echo ""
echo "常用命令:"
echo "  查看日志: tail -f $CRAWLER_LOG"
echo "  停止爬虫: ./stop_crawler.sh"
echo "  查看状态: ps aux | grep scheduler"
