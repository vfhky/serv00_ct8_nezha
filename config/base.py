# config/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

class ConfigBase(ABC):
    """
    配置基类，定义了配置的基本接口
    """

    @abstractmethod
    def __init__(self, file_path: str):
        """
        初始化配置

        Args:
            file_path: 配置文件路径
        """
        self.file_path = file_path
        self.config_data = {}

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键
            default: 默认值，如果配置项不存在则返回此值

        Returns:
            Any: 配置值
        """
        pass

    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置项

        Returns:
            Dict[str, Any]: 所有配置项
        """
        pass

    @abstractmethod
    def reload(self) -> bool:
        """
        重新加载配置

        Returns:
            bool: 重新加载是否成功
        """
        pass

    @abstractmethod
    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证配置

        Returns:
            Tuple[bool, List[str]]: 验证是否通过和错误消息列表
        """
        pass