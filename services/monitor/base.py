# core/monitor/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class MonitorBase(ABC):
    """
    监控基类，定义了监控的基本接口
    """
    
    @abstractmethod
    def check(self) -> bool:
        """
        执行监控检查
        
        Returns:
            bool: 检查是否通过
        """
        pass
    
    @abstractmethod
    def handle_failure(self, error: Any) -> None:
        """
        处理监控失败的情况
        
        Args:
            error: 失败原因
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        获取监控状态
        
        Returns:
            Dict[str, Any]: 监控状态的字典
        """
        pass