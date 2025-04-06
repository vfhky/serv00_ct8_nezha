# core/service_manager.py
import os
import time
import threading
import traceback
from typing import Dict, Any, Optional, List, Tuple, Callable

from config.loader import ConfigLoader
from utils.logger import get_logger
from utils.events import get_event_bus, EventTypes, EventBus
from utils.decorators import singleton

# 统一从services目录导入
from services.notification.manager import NotifierManager, notifier_manager
from services.backup.manager import BackupManager, backup_manager
from services.monitor.manager import MonitorManager, monitor_manager
from services.heartbeat.service import HeartbeatService, heartbeat_service
from services.installer.manager import InstallationManager, installation_manager

logger = get_logger()
event_bus = get_event_bus()

@singleton
class ServiceManager:
    """服务管理器，负责管理所有服务组件"""

    def __init__(self):
        self.config = None
        self.event_handlers = {}
        self.services_initialized = False
        self.services_started = False
        self.stop_requested = False
        self.watch_thread = None

        # 注册事件处理器
        self._register_event_handlers()

    def initialize(self, config_file: Optional[str] = None) -> bool:
        """初始化服务管理器"""
        try:
            logger.info("开始初始化服务管理器")

            # 初始化配置管理器
            if config_file:
                success = ConfigLoader.load_config_file(config_file)
            else:
                success = ConfigLoader.load_default_config()

            if not success:
                logger.error("加载配置失败，请确保配置文件存在且格式正确")
                return False

            # 获取系统配置
            self.config = ConfigLoader.get_config('sys')
            if not self.config:
                logger.error("获取系统配置失败")
                return False

            # 初始化各个服务组件
            notifier_manager.initialize(self.config)
            backup_manager.initialize(self.config)
            monitor_manager.initialize(self.config)
            installation_manager.initialize(self.config)
            heartbeat_service.initialize(self.config)

            self.services_initialized = True
            logger.info("服务管理器初始化成功")

            return True

        except Exception as e:
            logger.error(f"初始化服务管理器失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def start_services(self) -> bool:
        """启动所有服务"""
        try:
            if not self.services_initialized:
                logger.error("服务未初始化，无法启动")
                return False

            logger.info("开始启动服务")
            event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始启动服务")

            # 启动通知服务
            notifier_manager.start()

            # 启动备份服务
            backup_manager.start()

            # 启动监控服务
            monitor_manager.start()

            # 启动心跳服务
            heartbeat_service.start()

            # 启动服务状态监控线程
            self.stop_requested = False
            self.watch_thread = threading.Thread(target=self._watch_services, daemon=True)
            self.watch_thread.start()

            self.services_started = True
            logger.info("所有服务启动成功")
            event_bus.publish(EventTypes.SUCCESS_EVENT, message="所有服务启动成功")

            return True

        except Exception as e:
            logger.error(f"启动服务失败: {str(e)}")
            logger.error(traceback.format_exc())
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"启动服务失败: {str(e)}")
            return False

    def stop_services(self) -> bool:
        """停止所有服务"""
        try:
            logger.info("开始停止服务")
            event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始停止服务")

            # 请求停止监控线程
            self.stop_requested = True
            if self.watch_thread and self.watch_thread.is_alive():
                self.watch_thread.join(timeout=5)

            # 创建资源清理列表
            cleanup_tasks = [
                (notifier_manager.stop, "通知服务"),
                (backup_manager.stop, "备份服务"),
                (monitor_manager.stop, "监控服务"),
                (heartbeat_service.stop, "心跳服务"),
                (self._cleanup_resources, "服务管理器资源")
            ]

            # 执行所有清理任务，不因一个失败而中断
            for task, name in cleanup_tasks:
                try:
                    task()
                except Exception as e:
                    logger.error(f"停止{name}失败: {str(e)}")

            self.services_started = False
            logger.info("所有服务已停止")
            event_bus.publish(EventTypes.SYSTEM_EVENT, message="所有服务已停止")

            return True

        except Exception as e:
            logger.error(f"停止服务失败: {str(e)}")
            logger.error(traceback.format_exc())
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"停止服务失败: {str(e)}")
            return False

    def restart_services(self) -> bool:
        """重启所有服务"""
        self.stop_services()
        time.sleep(1)  # 等待服务完全停止
        return self.start_services()

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            'services_initialized': self.services_initialized,
            'services_started': self.services_started,
            'notifier': notifier_manager.get_status(),
            'backup': backup_manager.get_status(),
            'monitor': monitor_manager.get_status(),
            'heartbeat': heartbeat_service.get_status(),
            'installation': installation_manager.get_status()
        }

        return status

    def install_dashboard(self, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """安装哪吒面板"""
        return installation_manager.install_dashboard(params)

    def install_agent(self, server: str, key: str) -> Tuple[bool, str]:
        """安装哪吒Agent"""
        return installation_manager.install_agent(server, key)

    def uninstall_dashboard(self) -> Tuple[bool, str]:
        """卸载哪吒面板"""
        return installation_manager.uninstall_dashboard()

    def uninstall_agent(self) -> Tuple[bool, str]:
        """卸载哪吒Agent"""
        return installation_manager.uninstall_agent()

    def send_notification(self, message: str, level: str = "info",
                          channel: Optional[str] = None) -> bool:
        """发送通知"""
        return notifier_manager.notify_custom(message, level, channel=channel)

    def backup_files(self, files: List[str], backup_name: Optional[str] = None) -> bool:
        """备份文件"""
        return backup_manager.backup_files(files, backup_name)

    def subscribe_event(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """订阅事件"""
        event_bus.subscribe(event_type, callback)

    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """添加事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        event_bus.subscribe(event_type, handler)

    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """移除事件处理器"""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            event_bus.unsubscribe(event_type, handler)

    def _register_event_handlers(self) -> None:
        """注册默认事件处理器"""
        # 错误事件处理
        self.add_event_handler(EventTypes.ERROR_EVENT, self._handle_error_event)

        # 警告事件处理
        event_bus.subscribe(EventTypes.WARNING_EVENT, self._handle_warning_event)

        # 成功事件处理
        self.add_event_handler(EventTypes.SUCCESS_EVENT, self._handle_success_event)

        # 系统事件处理
        self.add_event_handler(EventTypes.SYSTEM_EVENT, self._handle_system_event)

        # 监控事件处理
        self.add_event_handler(EventTypes.MONITOR_EVENT, self._handle_monitor_event)

        # 备份事件处理
        self.add_event_handler(EventTypes.BACKUP_EVENT, self._handle_backup_event)

        # 心跳事件处理
        self.add_event_handler(EventTypes.HEARTBEAT_EVENT, self._handle_heartbeat_event)

    def _handle_system_event(self, event_type: str, **kwargs) -> None:
        """处理系统事件"""
        message = kwargs.get('message', '')
        logger.info(f"系统事件: {message}")

    def _handle_error_event(self, event_type: str, **kwargs) -> None:
        """处理错误事件"""
        message = kwargs.get('message', '')
        logger.error(f"错误事件: {message}")

        # 发送通知
        self.send_notification(f"错误: {message}", level="error")

    def _handle_warning_event(self, event_data: Dict[str, Any]) -> None:
        """处理警告事件"""
        if 'message' in event_data:
            logger.warning(event_data['message'])

            # 如果通知管理器已初始化，发送通知
            if self.services_initialized:
                notifier_manager.send_notification(event_data['message'], "warning")

    def _handle_success_event(self, event_type: str, **kwargs) -> None:
        """处理成功事件"""
        message = kwargs.get('message', '')
        logger.info(f"成功事件: {message}")

    def _handle_monitor_event(self, event_type: str, **kwargs) -> None:
        """处理监控事件"""
        status = kwargs.get('status', '')
        url = kwargs.get('url', '')
        message = kwargs.get('message', '')

        if status == 'success':
            logger.info(f"监控成功: {url}")
        else:
            logger.warning(f"监控失败: {url}, {message}")
            # 发送通知
            self.send_notification(f"监控失败: {url}, {message}", level="warning")

    def _handle_backup_event(self, event_type: str, **kwargs) -> None:
        """处理备份事件"""
        status = kwargs.get('status', '')
        file = kwargs.get('file', '')
        message = kwargs.get('message', '')

        if status == 'success':
            logger.info(f"备份成功: {file}")
        else:
            logger.warning(f"备份失败: {file}, {message}")
            # 发送通知
            self.send_notification(f"备份失败: {file}, {message}", level="warning")

    def _handle_heartbeat_event(self, event_type: str, **kwargs) -> None:
        """处理心跳事件"""
        status = kwargs.get('status', '')
        host = kwargs.get('host', '')
        message = kwargs.get('message', '')

        if status == 'success':
            logger.debug(f"心跳成功: {host}")
        else:
            logger.warning(f"心跳失败: {host}, {message}")
            # 发送通知
            self.send_notification(f"心跳失败: {host}, {message}", level="warning")

    def _watch_services(self) -> None:
        """监控服务状态的线程"""
        logger.info("服务状态监控线程已启动")

        while not self.stop_requested:
            try:
                # 检查各个服务状态
                if not notifier_manager.is_running():
                    logger.warning("通知服务已停止，尝试重启")
                    notifier_manager.start()

                if not backup_manager.is_running():
                    logger.warning("备份服务已停止，尝试重启")
                    backup_manager.start()

                if not monitor_manager.is_running():
                    logger.warning("监控服务已停止，尝试重启")
                    monitor_manager.start()

                if not heartbeat_service.is_running():
                    logger.warning("心跳服务已停止，尝试重启")
                    heartbeat_service.start()

                # 每分钟检查一次
                time.sleep(60)

            except Exception as e:
                logger.error(f"服务状态监控错误: {str(e)}")
                time.sleep(120)  # 错误后延长检查间隔

        logger.info("服务状态监控线程已停止")

    def _cleanup_resources(self) -> None:
        """清理资源"""
        logger.info("开始清理服务管理器资源")

        # 取消事件订阅
        for event_type, handlers in self.event_handlers.items():
            for handler in handlers:
                event_bus.unsubscribe(event_type, handler)

        self.event_handlers.clear()
        logger.info("服务管理器资源清理完成")

# 创建单例实例
service_manager = ServiceManager()