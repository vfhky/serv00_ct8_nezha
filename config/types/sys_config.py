# config/types/sys_config.py
import os
from typing import Any, Dict, List, Optional, Tuple
from config.base import ConfigBase
from utils.logger import get_logger

logger = get_logger()

class SysConfig(ConfigBase):
    """
    系统配置类，处理系统级配置
    """

    def __init__(self, file_path: str):
        """
        初始化系统配置

        Args:
            file_path: 配置文件路径

        Raises:
            FileNotFoundError: 配置文件不存在
            IOError: 读取配置文件错误
            ValueError: 配置文件格式错误
        """
        self.file_path = file_path
        self.config_data = {}

        if not os.path.exists(file_path):
            error_msg = f"配置文件不存在: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        self._parse_config_file()

        # 验证配置
        valid, errors = self.validate()
        if not valid:
            error_msg = f"配置验证失败: {', '.join(errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键
            default: 默认值，如果配置项不存在则返回此值

        Returns:
            Any: 配置值
        """
        return self.config_data.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置项

        Returns:
            Dict[str, Any]: 所有配置项
        """
        return self.config_data.copy()

    def reload(self) -> bool:
        """
        重新加载配置

        Returns:
            bool: 重新加载是否成功
        """
        try:
            old_config = self.config_data.copy()
            self._parse_config_file()

            # 验证配置
            valid, errors = self.validate()
            if not valid:
                self.config_data = old_config  # 恢复旧配置
                error_msg = f"配置验证失败: {', '.join(errors)}"
                logger.error(error_msg)
                return False

            logger.info(f"成功重新加载配置: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"重新加载配置失败: {self.file_path}: {str(e)}")
            return False

    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证配置

        Returns:
            Tuple[bool, List[str]]: 验证是否通过和错误消息列表
        """
        errors = []

        # 验证必要的配置项
        required_keys = [
            'notification_enabled',
            'monitor_interval',
            'heartbeat_interval',
            'install_dir',
            'log_level'
        ]

        for key in required_keys:
            if key not in self.config_data:
                errors.append(f"缺少必要的配置项: {key}")

        # 验证布尔值配置项
        bool_keys = ['notification_enabled', 'backup_enabled', 'debug_mode']
        for key in bool_keys:
            if key in self.config_data:
                value = self.config_data[key]
                if value.lower() not in ['true', 'false']:
                    errors.append(f"配置项 {key} 必须为布尔值(true/false): {value}")

        # 验证整数配置项
        int_keys = ['backup_interval', 'backup_retention', 'monitor_interval',
                    'monitor_retry', 'monitor_timeout', 'heartbeat_interval',
                    'heartbeat_timeout']
        for key in int_keys:
            if key in self.config_data:
                value = self.config_data[key]
                try:
                    int_value = int(value)
                    if int_value <= 0:
                        errors.append(f"配置项 {key} 必须为正整数: {value}")
                except (ValueError, TypeError):
                    errors.append(f"配置项 {key} 必须为整数: {value}")

        # 验证日志级别
        if 'log_level' in self.config_data:
            log_level = self.config_data['log_level']
            if log_level not in ['debug', 'info', 'warning', 'error']:
                errors.append(f"配置项 log_level 必须为 'debug', 'info', 'warning' 或 'error': {log_level}")

        # 验证通知级别
        if 'notification_level' in self.config_data:
            notification_level = self.config_data['notification_level']
            if notification_level not in ['info', 'warning', 'error']:
                errors.append(f"配置项 notification_level 必须为 'info', 'warning' 或 'error': {notification_level}")

        return len(errors) == 0, errors

    def _parse_config_file(self) -> None:
        """
        解析配置文件

        Raises:
            IOError: 读取配置文件错误
            ValueError: 配置文件格式错误
        """
        self.config_data = {}

        try:
            with open(self.file_path, 'r') as file:
                for line_number, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    if '=' not in line:
                        logger.warning(f"配置文件 {self.file_path} 第 {line_number} 行格式错误: {line}")
                        continue

                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # 处理布尔值
                    if value.lower() in ('true', 'yes', '1'):
                        value = 'true'
                    elif value.lower() in ('false', 'no', '0'):
                        value = 'false'

                    self.config_data[key] = value

            logger.info(f"成功加载配置: {self.file_path}")
        except IOError as e:
            error_msg = f"读取配置文件错误: {self.file_path} - {str(e)}"
            logger.error(error_msg)
            raise IOError(error_msg)