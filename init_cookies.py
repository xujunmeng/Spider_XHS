#!/usr/bin/env python3
# ============================================
# 初始化 Cookie 池
# ============================================

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from search_crawler.init_cookie_pool import init_cookie_pool


if __name__ == '__main__':
    init_cookie_pool()
