# config/loader.py
import os
import sys
from typing import Dict, Any, Optional, Type, List, Tuple
from config.base import ConfigBase
import importlib
from utils.logger import get_logger

logger = get_logger()

class ConfigLoader:
    """
    配置加载器，负责加载和管理各种配置
    """
    _instances: Dict[str, ConfigBase] = {}
    _config_types = ['sys', 'host', 'heartbeat', 'monitor']
    _config_paths = {
        'sys': 'config/sys.conf',
        'host': 'config/host.conf',
        'heartbeat': 'config/heartbeat.conf',
        'monitor': 'config/monitor.conf'
    }
    _template_paths = {
        'sys': 'config/sys.eg',
        'host': 'config/host.eg',
        'heartbeat': 'config/heartbeat.eg',
        'monitor': 'config/monitor.eg'
    }

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

        Raises:
            FileNotFoundError: 配置文件不存在
            ImportError: 无法导入配置类
            ValueError: 配置类型无效
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
                logger.error(f"无法加载配置类型 '{config_type}': {str(e)}")
                raise ValueError(f"无法加载配置类型 '{config_type}': {str(e)}")

        # 严格检查配置文件是否存在
        if not os.path.exists(file_path):
            error_msg = f"配置文件不存在: {file_path}"
            logger.error(error_msg)

            # 提示用户从模板创建配置文件
            template_path = ConfigLoader._template_paths.get(config_type)
            if template_path and os.path.exists(template_path):
                logger.info(f"请从模板创建配置文件: cp {template_path} {file_path}")

            raise FileNotFoundError(error_msg)

        # 实例化配置类
        try:
            config_instance = config_class(file_path)
            ConfigLoader._instances[config_type] = config_instance
            logger.info(f"成功加载配置: {config_type} 从 {file_path}")
            return config_instance
        except Exception as e:
            logger.error(f"加载配置失败: {config_type} 从 {file_path}: {str(e)}")
            raise

    @staticmethod
    def load_config_file(config_file: str) -> bool:
        """
        加载单个配置文件

        Args:
            config_file: 配置文件路径

        Returns:
            bool: 加载是否成功
        """
        if not os.path.exists(config_file):
            logger.error(f"配置文件不存在: {config_file}")
            return False

        # 根据文件名推断配置类型
        file_name = os.path.basename(config_file)
        config_type = file_name.split('.')[0]

        try:
            ConfigLoader.load_config(config_type, config_file)
            return True
        except Exception as e:
            logger.error(f"加载配置文件失败: {config_file}: {str(e)}")
            return False

    @staticmethod
    def load_default_config() -> bool:
        """
        加载所有默认配置文件

        Returns:
            bool: 所有配置是否成功加载
        """
        success = True

        # 检查所有配置文件是否存在
        missing_configs = []
        for config_type, config_path in ConfigLoader._config_paths.items():
            if not os.path.exists(config_path):
                missing_configs.append((config_type, config_path))

        # 如果有缺失的配置文件，输出错误信息并退出
        if missing_configs:
            logger.error("以下配置文件不存在:")
            for config_type, config_path in missing_configs:
                template_path = ConfigLoader._template_paths.get(config_type)
                if template_path and os.path.exists(template_path):
                    logger.error(f"  {config_path} (请从模板创建: cp {template_path} {config_path})")
                else:
                    logger.error(f"  {config_path}")
            return False

        # 加载所有配置
        for config_type, config_path in ConfigLoader._config_paths.items():
            try:
                ConfigLoader.load_config(config_type, config_path)
            except Exception as e:
                logger.error(f"加载配置失败: {config_type} 从 {config_path}: {str(e)}")
                success = False

        return success

    @staticmethod
    def get_config(config_type: str) -> Optional[ConfigBase]:
        """
        获取指定类型的配置实例

        Args:
            config_type: 配置类型

        Returns:
            Optional[ConfigBase]: 配置实例，如果不存在则返回None
        """
        return ConfigLoader._instances.get(config_type)

    @staticmethod
    def reload_config(config_type: str) -> bool:
        """
        重新加载指定类型的配置

        Args:
            config_type: 配置类型

        Returns:
            bool: 重新加载是否成功
        """
        if config_type not in ConfigLoader._config_paths:
            logger.error(f"未知的配置类型: {config_type}")
            return False

        config_path = ConfigLoader._config_paths[config_type]
        if not os.path.exists(config_path):
            logger.error(f"配置文件不存在: {config_path}")
            return False

        try:
            # 如果已经加载过，先移除
            if config_type in ConfigLoader._instances:
                del ConfigLoader._instances[config_type]

            ConfigLoader.load_config(config_type, config_path)
            logger.info(f"成功重新加载配置: {config_type}")
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败: {config_type}: {str(e)}")
            return False