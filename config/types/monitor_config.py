import os
from typing import Any, Dict, List, Optional, Tuple
from config.base import ConfigBase
from utils.logger import get_logger

logger = get_logger()

class MonitorConfig(ConfigBase):
    """
    监控配置类，处理监控相关配置
    """

    def __init__(self, file_path: str):
        """
        初始化监控配置

        Args:
            file_path: 配置文件路径
        """
        self.file_path = file_path
        self.config_data = {}
        self.monitors = []
        self._parse_config_file()

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
        return {
            'monitors': self.monitors.copy(),
            **self.config_data
        }

    def get_monitors(self) -> List[Dict[str, Any]]:
        """
        获取所有监控配置

        Returns:
            List[Dict[str, Any]]: 监控配置列表
        """
        return self.monitors.copy()

    def reload(self) -> bool:
        """
        重新加载配置

        Returns:
            bool: 重新加载是否成功
        """
        try:
            self._parse_config_file()
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

        # 验证监控配置
        for i, monitor in enumerate(self.monitors):
            if 'path' not in monitor:
                errors.append(f"监控 {i+1} 缺少 path")
            if 'process_name' not in monitor:
                errors.append(f"监控 {i+1} 缺少 process_name")
            if 'start_command' not in monitor:
                errors.append(f"监控 {i+1} 缺少 start_command")
            if 'type' not in monitor:
                errors.append(f"监控 {i+1} 缺少 type")
            elif monitor['type'] not in ['foreground', 'background']:
                errors.append(f"监控 {i+1} 的 type 必须为 'foreground' 或 'background'")

        return len(errors) == 0, errors

    def _parse_config_file(self) -> None:
        """
        解析配置文件

        Raises:
            IOError: 读取配置文件错误
            ValueError: 配置文件格式错误
        """
        self.monitors = []

        if not os.path.exists(self.file_path):
            logger.warning(f"配置文件不存在: {self.file_path}")
            return

        invalid_lines = []

        try:
            with open(self.file_path, 'r') as file:
                for line_number, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('|')
                    if len(parts) != 4:
                        invalid_lines.append((line_number, line, "格式错误，应为'path|process_name|start_command|type'"))
                        continue

                    path, process_name, start_command, monitor_type = parts
                    if monitor_type not in ['foreground', 'background']:
                        invalid_lines.append((line_number, line, f"类型'{monitor_type}'无效，必须为'foreground'或'background'"))
                        continue

                    self.monitors.append({
                        "path": path,
                        "process_name": process_name,
                        "start_command": start_command,
                        "type": monitor_type
                    })

            # 如果有无效行，记录警告
            if invalid_lines:
                for line_number, line, reason in invalid_lines:
                    logger.warning(f"配置文件 {self.file_path} 第 {line_number} 行无效: {line} - {reason}")

            logger.info(f"成功加载配置: {self.file_path}, 共 {len(self.monitors)} 个监控")
        except IOError as e:
            logger.error(f"读取配置文件错误: {self.file_path} - {str(e)}")
            raise IOError(f"读取配置文件错误: {self.file_path} - {str(e)}")
