# config/types/sys_config.py
from typing import Any, Dict, Optional
from config.base import ConfigBase

class SysConfig(ConfigBase):
    """
    系统配置类，处理系统级配置
    """
    _instance = None
    
    def __new__(cls, file_path: str):
        if cls._instance is None:
            cls._instance = super(SysConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, file_path: str):
        if getattr(self, '_initialized', False):
            return
        
        self._initialized = True
        self.file_path = file_path
        self.config = self._parse_config_file()
    
    def _parse_config_file(self) -> Dict[str, Any]:
        """
        解析配置文件
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        config = {}
        try:
            with open(self.file_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        except (IOError, OSError) as e:
            print(f"读取配置文件失败: {e}")
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值，如果键不存在则返回此值
            
        Returns:
            配置值或默认值
        """
        return self.config.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            Dict[str, Any]: 所有配置的字典
        """
        return self.config.copy()
    
    def reload(self) -> None:
        """
        重新加载配置
        """
        self.config = self._parse_config_file()