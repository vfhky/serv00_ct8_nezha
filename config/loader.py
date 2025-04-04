# config/loader.py
import os
from typing import Dict, Any, Optional, Type
from config.base import ConfigBase
import importlib

class ConfigLoader:
    """
    配置加载器，负责加载和管理各种配置
    """
    _instances: Dict[str, ConfigBase] = {}

    @staticmethod
    def load_config(config_type: str, file_path: str, config_class: Optional[Type[ConfigBase]] = None) -> ConfigBase:
        """
        加载指定类型的配置

        Args:
            config_type: 配置类型，如 'sys', 'host', 'heartbeat'
            file_path: 配置文件路径
            config_class: 配置类，如果不指定，会尝试自动导入

        Returns:
            ConfigBase: 配置实例
        """
        # 检查配置是否已加载
        if config_type in ConfigLoader._instances:
            return ConfigLoader._instances[config_type]

        # 如果没有指定配置类，尝试自动导入
        if config_class is None:
            try:
                module = importlib.import_module(f"config.types.{config_type}_config")
                # 获取配置类名，通常是类型名称首字母大写加Config
                class_name = f"{config_type.capitalize()}Config"
                config_class = getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                raise ValueError(f"无法加载配置类型 '{config_type}': {str(e)}")

        # 确保文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        # 实例化配置类
        config_instance = config_class(file_path)
        ConfigLoader._instances[config_type] = config_instance

        return config_instance

    @staticmethod
    def get_config(config_type: str) -> Optional[ConfigBase]:
        """
        获取已加载的配置

        Args:
            config_type: 配置类型

        Returns:
            Optional[ConfigBase]: 配置实例，如果不存在则返回None
        """
        return ConfigLoader._instances.get(config_type)

    @staticmethod
    def reload_config(config_type: str) -> Optional[ConfigBase]:
        """
        重新加载配置

        Args:
            config_type: 配置类型

        Returns:
            Optional[ConfigBase]: 重新加载后的配置实例，如果不存在则返回None
        """
        config = ConfigLoader.get_config(config_type)
        if config:
            config.reload()
        return config

    @staticmethod
    def reload_all() -> None:
        """
        重新加载所有配置
        """
        for config in ConfigLoader._instances.values():
            config.reload()

    @staticmethod
    def load_default_config() -> bool:
        """
        加载默认配置文件

        Returns:
            bool: 加载是否成功
        """
        try:
            # 获取默认配置文件路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            default_config_path = os.path.join(project_root, 'config', 'config.ini')

            # 检查文件是否存在
            if not os.path.exists(default_config_path):
                from utils.logger import get_logger
                logger = get_logger()
                logger.error(f"默认配置文件不存在: {default_config_path}")
                return False

            # 加载系统配置
            ConfigLoader.load_config('sys', default_config_path)
            return True
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger()
            logger.error(f"加载默认配置失败: {str(e)}")
            return False