import os
import time
import requests
from typing import Dict, Any, Optional, List, Tuple

from services.monitor.base import MonitorBase
from config.base import ConfigBase
from utils.logger import get_logger
from utils.events import get_event_bus, EventTypes

logger = get_logger()
event_bus = get_event_bus()

class UrlMonitor(MonitorBase):
    """
    URL监控，定期检查URL可访问性
    """
    
    def __init__(self, url: str, expected_status: int = 200, check_interval: int = 300):
        """
        初始化URL监控
        
        Args:
            url: 要监控的URL
            expected_status: 预期的HTTP状态码
            check_interval: 检查间隔（秒）
        """
        self.url = url
        self.expected_status = expected_status
        self.check_interval = check_interval
        self.last_check_time = 0
        self.last_status_code = 0
        self.last_response_time = 0
    
    def check(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检查URL状态
        
        Returns:
            Tuple[bool, str, Dict[str, Any]]: URL是否可访问、消息和详细信息
        """
        current_time = time.time()
        
        # 如果距离上次检查时间不足间隔时间，则返回上次结果
        if current_time - self.last_check_time < self.check_interval:
            is_ok = self.last_status_code == self.expected_status
            return is_ok, f"使用缓存结果, URL: {self.url}, 状态码: {self.last_status_code}", {
                'url': self.url,
                'status_code': self.last_status_code,
                'expected_status': self.expected_status,
                'response_time': self.last_response_time,
                'last_check': self.last_check_time
            }
        
        self.last_check_time = current_time
        
        try:
            # 发送请求
            start_time = time.time()
            response = requests.get(self.url, timeout=10)
            end_time = time.time()
            
            self.last_status_code = response.status_code
            self.last_response_time = round((end_time - start_time) * 1000, 2)  # 毫秒
            
            is_ok = self.last_status_code == self.expected_status
            message = f"URL: {self.url}, 状态码: {self.last_status_code}, 响应时间: {self.last_response_time}ms"
            
            if not is_ok:
                logger.warning(f"URL监控异常: {message}")
                event_bus.publish(EventTypes.WARNING_EVENT, message=f"URL监控异常: {message}")
            
            return is_ok, message, {
                'url': self.url,
                'status_code': self.last_status_code,
                'expected_status': self.expected_status,
                'response_time': self.last_response_time,
                'last_check': self.last_check_time,
                'content_length': len(response.content) if response.content else 0
            }
            
        except requests.RequestException as e:
            self.last_status_code = 0
            self.last_response_time = 0
            
            message = f"URL: {self.url}, 访问失败: {str(e)}"
            logger.error(f"URL监控异常: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"URL监控异常: {message}")
            
            return False, message, {
                'url': self.url,
                'status_code': 0,
                'expected_status': self.expected_status,
                'response_time': 0,
                'last_check': self.last_check_time,
                'error': str(e)
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取监控指标
        
        Returns:
            Dict[str, Any]: 监控指标数据
        """
        is_ok, _, details = self.check()
        
        return {
            'url': self.url,
            'available': is_ok,
            'status_code': self.last_status_code,
            'response_time': self.last_response_time,
            'last_check': self.last_check_time
        }
