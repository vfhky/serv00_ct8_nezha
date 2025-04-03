# services/notification/base.py
from abc import ABC, abstractmethod
from typing import Any, Optional

class NotifierBase(ABC):
    """
    通知服务基类，定义了通知的基本接口
    """
    
    @abstractmethod
    def notify(self, message: str, level: str = 'info', **kwargs: Any) -> bool:
        """
        发送通知
        
        Args:
            message: 通知内容
            level: 通知级别，如 'info', 'warning', 'error'
            **kwargs: 其他参数
            
        Returns:
            bool: 通知是否发送成功
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        检查通知服务是否启用
        
        Returns:
            bool: 服务是否启用
        """
        pass