# config/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ConfigBase(ABC):
    """
    配置基类，定义了配置的基本接口
    """
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值，如果键不存在则返回此值
            
        Returns:
            配置值或默认值
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            所有配置的字典
        """
        pass
    
    @abstractmethod
    def reload(self) -> None:
        """
        重新加载配置
        """
        pass