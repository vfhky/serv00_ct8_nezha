from typing import Dict, List, Callable, Any, Optional
from utils.logger import get_logger
from utils.decorators import singleton

logger = get_logger()

@singleton
class EventBus:
    """
    事件总线，用于组件间的解耦通信
    """

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(f"已订阅事件 {event_type}: {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """
        取消订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"已取消订阅事件 {event_type}: {handler.__name__}")

    def publish(self, event_type: str, **kwargs: Any) -> None:
        """
        发布事件

        Args:
            event_type: 事件类型
            **kwargs: 事件参数
        """
        if event_type not in self._handlers:
            return

        logger.debug(f"发布事件: {event_type}, 参数: {kwargs}")

        for handler in self._handlers[event_type]:
            try:
                handler(**kwargs)
            except Exception as e:
                logger.error(f"事件处理器异常 {event_type} -> {handler.__name__}: {str(e)}")

# 单例获取方法
def get_event_bus() -> EventBus:
    """
    获取事件总线实例

    Returns:
        EventBus: 事件总线实例
    """
    return EventBus()

# 常用事件类型
class EventTypes:
    # 系统事件
    SYSTEM_STARTUP = "system:startup"
    SYSTEM_SHUTDOWN = "system:shutdown"

    # 配置事件
    CONFIG_LOADED = "config:loaded"
    CONFIG_UPDATED = "config:updated"

    # 监控事件
    MONITOR_STARTED = "monitor:started"
    MONITOR_STOPPED = "monitor:stopped"
    MONITOR_CHECK_SUCCESS = "monitor:check:success"
    MONITOR_CHECK_FAILURE = "monitor:check:failure"

    # 心跳事件
    HEARTBEAT_STARTED = "heartbeat:started"
    HEARTBEAT_COMPLETED = "heartbeat:completed"
    HEARTBEAT_FAILURE = "heartbeat:failure"

    # 进程事件
    PROCESS_STARTED = "process:started"
    PROCESS_STOPPED = "process:stopped"
    PROCESS_RESTARTED = "process:restarted"

    # 通知事件
    NOTIFICATION_SENT = "notification:sent"
    NOTIFICATION_FAILED = "notification:failed"

    # 备份事件
    BACKUP_STARTED = "backup:started"
    BACKUP_COMPLETED = "backup:completed"
    BACKUP_FAILED = "backup:failed"

# 辅助装饰器
def event_listener(event_type: str):
    """
    事件监听器装饰器

    Args:
        event_type: 事件类型

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable):
        get_event_bus().subscribe(event_type, func)
        return func
    return decorator
