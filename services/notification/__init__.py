# This file is intentionally left empty to mark directory as Python package

from services.notification.base import NotifierBase
from services.notification.factory import NotificationFactory
from services.notification.qywx import QywxNotifier
from services.notification.qywx_app import QywxAppNotifier
from services.notification.tg import TelegramNotifier
from services.notification.pushplus import PushPlusNotifier

# 导出工厂方法
notify_all = NotificationFactory.notify_all
get_notifier = NotificationFactory.get_notifier
create_notifiers = NotificationFactory.create_notifiers
get_enabled_notifiers = NotificationFactory.get_enabled_notifiers

__all__ = [
    'NotifierBase',
    'NotificationFactory',
    'QywxNotifier',
    'QywxAppNotifier',
    'TelegramNotifier',
    'PushPlusNotifier',
    'notify_all',
    'get_notifier',
    'create_notifiers',
    'get_enabled_notifiers'
]
