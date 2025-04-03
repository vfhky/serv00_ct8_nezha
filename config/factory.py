# config/factory.py
from typing import Any, Dict, Optional, Type
from config.base import ConfigBase
from config.loader import ConfigLoader
import os

class ConfigFactory:
    """
    配置工厂，负责创建和获取各种配置实例
    """
    
    @staticmethod
    def create_config(config_type: str, file_path: str, config_class: Optional[Type[ConfigBase]] = None) -> ConfigBase:
        """
        创建配置实例
        
        Args:
            config_type: 配置类型
            file_path: 配置文件路径
            config_class: 配置类，如果不指定，会尝试自动导入
            
        Returns:
            ConfigBase: 配置实例
        """
        return ConfigLoader.load_config(config_type, file_path, config_class)
    
    @staticmethod
    def get_config(config_type: str) -> Optional[ConfigBase]:
        """
        获取配置实例
        
        Args:
            config_type: 配置类型
            
        Returns:
            Optional[ConfigBase]: 配置实例，如果不存在则返回None
        """
        return ConfigLoader.get_config(config_type)
    
    @staticmethod
    def ensure_config_exists(config_path: str, template_path: str) -> None:
        """
        确保配置文件存在，不存在则从模板创建
        
        Args:
            config_path: 配置文件路径
            template_path: 模板文件路径
        """
        if not os.path.exists(config_path) and os.path.exists(template_path):
            with open(template_path, 'r') as template_file:
                template_content = template_file.read()
            
            with open(config_path, 'w') as config_file:
                config_file.write(template_content)