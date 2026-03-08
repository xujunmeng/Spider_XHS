#!/usr/bin/env python3
# ============================================
# Cookie 池初始化脚本
# 注意：运行前需先手动执行 init.sql 创建数据库表
# ============================================

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import DB_CONFIG, COOKIE_POOL
from .models import DatabaseManager
from .cookie_pool_manager import CookiePoolManager


def init_cookie_pool():
    """初始化 Cookie 池"""
    print("=" * 60)
    print("Cookie 池初始化工具")
    print("=" * 60)
    
    # 确保已手动执行 SQL 脚本创建表
    db_manager = DatabaseManager(DB_CONFIG['url'])
    cookie_manager = CookiePoolManager(db_manager)
    
    # 检查是否有配置 Cookie
    if not COOKIE_POOL or not any(c.get('value') for c in COOKIE_POOL):
        print("\n⚠️ 警告: config.py 中未配置有效的 Cookie")
        print("请先在 config.py 的 COOKIE_POOL 列表中添加 Cookie 值")
        print("\nCookie 格式示例:")
        print('  COOKIE_POOL = [')
        print('      {')
        print("          'name': 'account_01',")
        print("          'value': 'acw_tc=xxx; a1=xxx; web_session=xxx; ...',")
        print("          'account_info': '主账号'")
        print("      },")
        print("  ]")
        return
    
    # 导入 Cookie
    print(f"\n发现 {len(COOKIE_POOL)} 个 Cookie 配置")
    print("正在导入到数据库...\n")
    
    success_count = 0
    for cookie_info in COOKIE_POOL:
        cookie_value = cookie_info.get('value', '').strip()
        if not cookie_value:
            print(f"  ⚠️ 跳过 [{cookie_info['name']}]: Cookie 值为空")
            continue
        
        try:
            cookie_manager.add_cookie(
                cookie_info['name'],
                cookie_value,
                cookie_info.get('account_info', '')
            )
            print(f"  ✅ 导入成功: {cookie_info['name']}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ 导入失败 [{cookie_info['name']}]: {e}")
    
    print(f"\n导入完成: {success_count}/{len(COOKIE_POOL)} 成功")
    
    # 打印当前状态
    print("\n当前 Cookie 池状态:")
    cookie_manager.print_pool_status()
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    init_cookie_pool()
