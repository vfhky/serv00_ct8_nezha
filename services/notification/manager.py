from typing import Dict, Any, Optional
from services.notification.factory import NotificationFactory
from config.base import ConfigBase
from utils.logger import get_logger
from utils.decorators import singleton

logger = get_logger()

@singleton
class NotifierManager:
    """
    通知管理器，用于处理各种通知场景
    """

    def __init__(self):
        self.config = None

    def initialize(self, config: ConfigBase) -> None:
        """
        初始化通知管理器

        Args:
            config: 配置实例
        """
        self.config = config
        # 创建所有通知实现
        NotificationFactory.create_notifiers(config)

    def notify_monitor_success(self, url: str, response: Dict[str, Any]) -> bool:
        """
        发送监控成功通知

        Args:
            url: 监控的URL
            response: 响应信息

        Returns:
            bool: 通知是否发送成功
        """
        message = f"监控域名访问成功\n\n域名: {url}\n状态码: {response.get('status_code', 200)}"
        return NotificationFactory.notify_all(message, level='info')

    def notify_monitor_failure(self, url: str, error: Any) -> bool:
        """
        发送监控失败通知

        Args:
            url: 监控的URL
            error: 错误信息

        Returns:
            bool: 通知是否发送成功
        """
        if hasattr(error, 'status_code'):
            message = f"监控域名访问失败\n\n域名: {url}\n状态码: {error.status_code}\n错误: {error.text if hasattr(error, 'text') else str(error)}"
        else:
            message = f"监控域名访问失败\n\n域名: {url}\n错误: {str(error)}"

        return NotificationFactory.notify_all(message, level='error')

    def notify_dns_failure(self, url: str, error: Any) -> bool:
        """
        发送DNS解析失败通知

        Args:
            url: 监控的URL
            error: 错误信息

        Returns:
            bool: 通知是否发送成功
        """
        message = f"监控域名DNS解析失败\n\n域名: {url}\n错误: {str(error)}"
        return NotificationFactory.notify_all(message, level='error')

    def notify_process_restart(self, process_name: str, app_path: str) -> bool:
        """
        发送进程重启通知

        Args:
            process_name: 进程名称
            app_path: 应用路径

        Returns:
            bool: 通知是否发送成功
        """
        message = f"进程已重启\n\n进程: {process_name}\n路径: {app_path}"
        return NotificationFactory.notify_all(message, level='warning')

    def notify_backup_success(self, db_file: str, backup_path: str) -> bool:
        """
        发送备份成功通知

        Args:
            db_file: 数据库文件
            backup_path: 备份路径

        Returns:
            bool: 通知是否发送成功
        """
        message = f"数据库备份成功\n\n文件: {db_file}\n备份路径: {backup_path}"
        return NotificationFactory.notify_all(message, level='info')

    def notify_backup_failure(self, db_file: str, error: Any) -> bool:
        """
        发送备份失败通知

        Args:
            db_file: 数据库文件
            error: 错误信息

        Returns:
            bool: 通知是否发送成功
        """
        message = f"数据库备份失败\n\n文件: {db_file}\n错误: {str(error)}"
        return NotificationFactory.notify_all(message, level='error')

    def notify_heartbeat_failure(self, hostname: str, username: str, error: Any) -> bool:
        """
        发送心跳失败通知

        Args:
            hostname: 主机名
            username: 用户名
            error: 错误信息

        Returns:
            bool: 通知是否发送成功
        """
        message = f"主机心跳失败\n\n主机: {username}@{hostname}\n错误: {str(error)}"
        return NotificationFactory.notify_all(message, level='error')

    def notify_custom(self, message: str, level: str = 'info', **kwargs) -> bool:
        """
        发送自定义通知

        Args:
            message: 通知内容
            level: 通知级别
            **kwargs: 其他参数

        Returns:
            bool: 通知是否发送成功
        """
        return NotificationFactory.notify_all(message, level, **kwargs)

# 创建单例实例
notifier_manager = NotifierManager()
