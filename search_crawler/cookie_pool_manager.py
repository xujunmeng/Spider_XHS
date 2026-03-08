# ============================================
# Cookie 池管理器
# ============================================

import random
import time
from datetime import datetime
from sqlalchemy import func
from loguru import logger
from .models import DatabaseManager, CookiePool, CookieUsageLog


class CookiePoolManager:
    """Cookie池管理器"""
    
    def __init__(self, db_manager, max_fail_count=5):
        """
        :param db_manager: DatabaseManager实例
        :param max_fail_count: 单Cookie最大失败次数
        """
        self.db_manager = db_manager
        self.max_fail_count = max_fail_count
        self.current_cookie = None
        self.current_cookie_name = None
    
    def add_cookie(self, cookie_name, cookie_value, account_info=''):
        """添加新Cookie到池中"""
        session = self.db_manager.get_session()
        try:
            existing = session.query(CookiePool).filter_by(cookie_name=cookie_name).first()
            
            if existing:
                existing.cookie_value = cookie_value
                existing.account_info = account_info
                existing.status = 1
                existing.fail_count = 0
            else:
                new_cookie = CookiePool(
                    cookie_name=cookie_name,
                    cookie_value=cookie_value,
                    account_info=account_info,
                    status=1
                )
                session.add(new_cookie)
            
            session.commit()
            logger.info(f"Cookie [{cookie_name}] 已添加到池中")
        except Exception as e:
            session.rollback()
            logger.error(f"添加Cookie失败: {e}")
        finally:
            session.close()
    
    def get_available_cookie(self, strategy='round_robin'):
        """
        获取可用的Cookie
        :param strategy: 选择策略 round_robin/random/least_used
        """
        session = self.db_manager.get_session()
        try:
            query = session.query(CookiePool).filter_by(status=1)
            
            if strategy == 'round_robin':
                query = query.order_by(CookiePool.last_used_time.asc())
            elif strategy == 'random':
                query = query.order_by(func.rand())
            elif strategy == 'least_used':
                query = query.order_by(CookiePool.use_count.asc())
            
            result = query.first()
            
            if result:
                self.current_cookie_name = result.cookie_name
                self.current_cookie = result.cookie_value
                
                result.last_used_time = datetime.now()
                result.use_count += 1
                session.commit()
                
                return result.cookie_name, result.cookie_value
            else:
                logger.error("没有可用的Cookie，请检查Cookie池")
                return None, None
        finally:
            session.close()
    
    def report_cookie_result(self, cookie_name, is_success, error_msg=None):
        """报告Cookie使用结果"""
        session = self.db_manager.get_session()
        try:
            cookie = session.query(CookiePool).filter_by(cookie_name=cookie_name).first()
            
            if cookie:
                if is_success:
                    cookie.success_count += 1
                    cookie.last_success_time = datetime.now()
                else:
                    cookie.fail_count += 1
                    
                    if cookie.fail_count >= self.max_fail_count:
                        cookie.status = 0
                        logger.warning(f"Cookie [{cookie_name}] 连续失败{self.max_fail_count}次，已标记为失效")
                
                session.commit()
            
            usage_log = CookieUsageLog(
                cookie_name=cookie_name,
                is_success=1 if is_success else 0,
                error_msg=error_msg
            )
            session.add(usage_log)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"报告Cookie结果失败: {e}")
        finally:
            session.close()
    
    def get_pool_status(self):
        """获取Cookie池状态统计"""
        session = self.db_manager.get_session()
        try:
            results = session.query(
                CookiePool.status,
                func.count().label('count'),
                func.sum(CookiePool.use_count).label('total_use'),
                func.sum(CookiePool.success_count).label('total_success'),
                func.sum(CookiePool.fail_count).label('total_fail')
            ).group_by(CookiePool.status).all()
            
            return results
        finally:
            session.close()
    
    def print_pool_status(self):
        """打印Cookie池状态"""
        status = self.get_pool_status()
        
        print("=" * 60)
        print("Cookie池状态")
        print("=" * 60)
        
        status_map = {0: '失效', 1: '正常', 2: '冻结'}
        
        for item in status:
            status_name = status_map.get(item.status, '未知')
            print(f"状态 [{status_name}]: {item.count} 个")
            print(f"  - 总使用次数: {item.total_use or 0}")
            print(f"  - 成功: {item.total_success or 0} | 失败: {item.total_fail or 0}")
            
            if item.total_use and item.total_use > 0:
                success_rate = (item.total_success or 0) / item.total_use * 100
                print(f"  - 成功率: {success_rate:.1f}%")
        print("=" * 60)


class CookiePoolDecorator:
    """Cookie池装饰器 - 为API请求自动管理Cookie"""
    
    def __init__(self, cookie_pool_manager):
        self.cookie_manager = cookie_pool_manager
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            max_retry = 3
            for i in range(max_retry):
                cookie_name, cookie = self.cookie_manager.get_available_cookie()
                if not cookie:
                    raise Exception("没有可用的Cookie")
                
                try:
                    result = func(*args, cookies_str=cookie, **kwargs)
                    
                    if isinstance(result, tuple) and len(result) >= 2:
                        success = result[0]
                        msg = result[1] if len(result) > 1 else ''
                        
                        if not success and self._is_cookie_invalid(msg):
                            self.cookie_manager.report_cookie_result(cookie_name, False, msg)
                            logger.warning(f"Cookie失效，自动切换 [{cookie_name}] -> 下一个")
                            continue
                        else:
                            self.cookie_manager.report_cookie_result(cookie_name, success)
                            return result
                    else:
                        self.cookie_manager.report_cookie_result(cookie_name, True)
                        return result
                        
                except Exception as e:
                    error_msg = str(e)
                    self.cookie_manager.report_cookie_result(cookie_name, False, error_msg)
                    
                    if self._is_cookie_invalid(error_msg) and i < max_retry - 1:
                        logger.warning(f"请求异常，切换Cookie重试 [{i+1}/{max_retry}]")
                        continue
                    else:
                        raise
            
            raise Exception(f"重试{max_retry}次后仍然失败")
        
        return wrapper
    
    def _is_cookie_invalid(self, error_msg):
        """判断错误是否由Cookie失效导致"""
        invalid_keywords = [
            '登录', 'cookie', 'session', '失效', '过期',
            '未登录', '鉴权', 'auth', 'forbidden', 'unauthorized'
        ]
        error_lower = str(error_msg).lower()
        return any(keyword in error_lower for keyword in invalid_keywords)
