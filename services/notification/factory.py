from typing import Dict, List, Optional, Type
from services.notification.base import NotifierBase
from config.base import ConfigBase
from utils.logger import get_logger

logger = get_logger()

class NotificationFactory:
    """
    通知服务工厂，负责创建和管理各种通知实现
    """
    _notifiers: Dict[str, NotifierBase] = {}

    @staticmethod
    def register_notifier(name: str, notifier: NotifierBase) -> None:
        """
        注册通知实现

        Args:
            name: 通知名称
            notifier: 通知实例
        """
        NotificationFactory._notifiers[name] = notifier
        logger.info(f"已注册通知服务: {name}")

    @staticmethod
    def get_notifier(name: str) -> Optional[NotifierBase]:
        """
        获取通知实现

        Args:
            name: 通知名称

        Returns:
            Optional[NotifierBase]: 通知实例，如果不存在则返回None
        """
        return NotificationFactory._notifiers.get(name)

    @staticmethod
    def create_notifiers(config: ConfigBase) -> Dict[str, NotifierBase]:
        """
        根据配置创建所有可用的通知实现

        Args:
            config: 配置实例

        Returns:
            Dict[str, NotifierBase]: 通知名称到通知实例的映射
        """
        # 导入已创建的单例实例
        from services.notification.qywx import qywx_notifier
        from services.notification.qywx_app import qywx_app_notifier
        from services.notification.tg import tg_notifier
        from services.notification.pushplus import pushplus_notifier

        # 接下来应该是使用这些实例，但我之前没有正确实现这部分
        # 正确的实现应该是：
        qywx_notifier.__class__.initialize.__func__(qywx_notifier.__class__, config)
        qywx_app_notifier.__class__.initialize.__func__(qywx_app_notifier.__class__, config)
        tg_notifier.__class__.initialize.__func__(tg_notifier.__class__, config)
        pushplus_notifier.__class__.initialize.__func__(pushplus_notifier.__class__, config)

        return NotificationFactory._notifiers

    @staticmethod
    def get_enabled_notifiers() -> List[NotifierBase]:
        """
        获取所有已启用的通知实现

        Returns:
            List[NotifierBase]: 已启用的通知实例列表
        """
        return [notifier for notifier in NotificationFactory._notifiers.values() if notifier.is_enabled()]

    @staticmethod
    def notify_all(message: str, level: str = 'info', **kwargs) -> bool:
        """
        向所有已启用的通知服务发送消息

        Args:
            message: 通知内容
            level: 通知级别，如 'info', 'warning', 'error'
            **kwargs: 其他参数

        Returns:
            bool: 是否至少有一个通知发送成功
        """
        notifiers = NotificationFactory.get_enabled_notifiers()
        if not notifiers:
            logger.warning("没有启用的通知服务")
            return False

        success = False
        for notifier in notifiers:
            try:
                if notifier.notify(message, level, **kwargs):
                    success = True
            except Exception as e:
                logger.error(f"通知失败: {notifier.__class__.__name__}, 错误: {str(e)}")

        return success
