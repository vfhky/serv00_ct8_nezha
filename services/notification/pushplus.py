import json
from typing import Optional, Dict, Any
import requests
from services.notification.base import NotifierBase
from services.notification.factory import NotificationFactory
from config.base import ConfigBase
from utils.logger import get_logger

logger = get_logger()

class PushPlusNotifier(NotifierBase):
    """
    PushPlus通知实现
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PushPlusNotifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        self._initialized = True
        self.enabled = False
        self.push_key = None
    
    @classmethod
    def initialize(cls, config: ConfigBase) -> 'PushPlusNotifier':
        """
        初始化通知实例
        
        Args:
            config: 配置实例
            
        Returns:
            PushPlusNotifier: 通知实例
        """
        instance = cls()
        instance.enabled = config.get('ENABLE_PUSHPLUS_NOTIFY') == '1'
        instance.push_key = config.get('PUSHPLUS_KEY')
        
        if instance.enabled and not instance.push_key:
            logger.warning("PushPlus通知已启用，但未配置密钥")
            instance.enabled = False
        
        # 注册到工厂
        NotificationFactory.register_notifier('pushplus', instance)
        
        return instance
    
    def is_enabled(self) -> bool:
        """
        检查通知服务是否启用
        
        Returns:
            bool: 服务是否启用
        """
        return self.enabled and self.push_key is not None
    
    def notify(self, message: str, level: str = 'info', **kwargs) -> bool:
        """
        发送通知
        
        Args:
            message: 通知内容
            level: 通知级别，如 'info', 'warning', 'error'
            **kwargs: 其他参数
            
        Returns:
            bool: 通知是否发送成功
        """
        if not self.is_enabled():
            logger.warning("PushPlus通知未启用")
            return False
        
        # 根据级别设置标题
        if level == 'error':
            title = '🚨 错误通知'
        elif level == 'warning':
            title = '⚠️ 警告通知'
        else:
            title = '📢 信息通知'
        
        # 构建请求数据
        data = {
            "token": self.push_key,
            "title": title,
            "content": message,
            "template": "html",
            "channel": "wechat"
        }
        
        # 发送请求
        url = "https://www.pushplus.plus/send"
        try:
            response = requests.post(
                url=url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(data),
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    logger.info(f"PushPlus通知发送成功")
                    return True
                else:
                    logger.error(f"PushPlus通知发送失败: {result.get('msg')}")
            else:
                logger.error(f"PushPlus通知发送失败，状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"PushPlus通知发送异常: {str(e)}")
        
        return False

# 创建实例并注册
pushplus_notifier = PushPlusNotifier()
