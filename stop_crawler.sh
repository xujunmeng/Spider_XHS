#!/bin/bash
# ============================================
# 小红书爬虫停止脚本
# ============================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/crawler.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️ 没有找到 PID 文件，爬虫可能未运行"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "🛑 停止爬虫 (PID: $PID)..."
    kill "$PID"
    
    # 等待进程结束
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ 爬虫已停止"
            rm "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    # 强制结束
    echo "⚠️ 强制结束进程..."
    kill -9 "$PID"
    rm "$PID_FILE"
    echo "✅ 爬虫已强制停止"
else
    echo "⚠️ 进程不存在 (PID: $PID)"
    rm "$PID_FILE"
fi
