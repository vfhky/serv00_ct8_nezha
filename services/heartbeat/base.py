from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple

class HeartbeatBase(ABC):
    """
    心跳基类，定义了心跳检测的基本接口
    """
    
    @abstractmethod
    def check(self) -> Tuple[bool, str]:
        """
        执行心跳检测
        
        Returns:
            Tuple[bool, str]: 检测是否成功和消息
        """
        pass
    
    @abstractmethod
    def handle_failure(self) -> bool:
        """
        处理心跳失败的情况
        
        Returns:
            bool: 处理是否成功
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        获取心跳状态
        
        Returns:
            Dict[str, Any]: 心跳状态信息
        """
        pass
