# core/service_manager.py
import os
import time
import threading
import traceback
from typing import Dict, Any, Optional, List, Tuple, Callable

from config.base import ConfigBase
from config.manager import config_manager
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
    """
    服务管理器，负责管理所有服务组件
    """

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
        """
        初始化服务管理器

        Args:
            config_file: 配置文件路径，如果不指定则使用默认路径

        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("开始初始化服务管理器")

            # 初始化配置管理器
            if config_file:
                success = config_manager.load_config(config_file)
            else:
                success = config_manager.load_default_config()

            if not success:
                logger.error("加载配置失败")
                return False

            self.config = config_manager.get_config()

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
        """
        启动所有服务

        Returns:
            bool: 启动是否成功
        """
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
        """
        停止所有服务

        Returns:
            bool: 停止是否成功
        """
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
        """
        重启所有服务

        Returns:
            bool: 重启是否成功
        """
        self.stop_services()
        time.sleep(1)  # 等待服务完全停止
        return self.start_services()

    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态

        Returns:
            Dict[str, Any]: 服务状态信息
        """
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
        """
        安装哪吒面板

        Args:
            params: 配置参数

        Returns:
            Tuple[bool, str]: 安装是否成功和消息
        """
        return installation_manager.install_dashboard(params)

    def install_agent(self, server: str, key: str) -> Tuple[bool, str]:
        """
        安装哪吒Agent

        Args:
            server: 服务器地址
            key: Agent Key

        Returns:
            Tuple[bool, str]: 安装是否成功和消息
        """
        return installation_manager.install_agent(server, key)

    def uninstall_dashboard(self) -> Tuple[bool, str]:
        """
        卸载哪吒面板

        Returns:
            Tuple[bool, str]: 卸载是否成功和消息
        """
        return installation_manager.uninstall_dashboard()

    def uninstall_agent(self) -> Tuple[bool, str]:
        """
        卸载哪吒Agent

        Returns:
            Tuple[bool, str]: 卸载是否成功和消息
        """
        return installation_manager.uninstall_agent()

    def send_notification(self, message: str, level: str = "info",
                          channel: Optional[str] = None) -> bool:
        """
        发送通知

        Args:
            message: 通知消息
            level: 通知级别，info/warning/error
            channel: 通知渠道，不指定则使用所有已启用的渠道

        Returns:
            bool: 发送是否成功
        """
        return notifier_manager.send_notification(message, level, channel)

    def backup_files(self, files: List[str], backup_name: Optional[str] = None) -> bool:
        """
        备份文件

        Args:
            files: 要备份的文件列表
            backup_name: 备份任务名称，不指定则使用时间戳

        Returns:
            bool: 备份是否成功
        """
        return backup_manager.backup_files(files, backup_name)

    def subscribe_event(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        event_bus.subscribe(event_type, callback)

    def _register_event_handlers(self) -> None:
        """
        注册事件处理器
        """
        # 错误事件处理
        event_bus.subscribe(EventTypes.ERROR_EVENT, self._handle_error_event)

        # 警告事件处理
        event_bus.subscribe(EventTypes.WARNING_EVENT, self._handle_warning_event)

        # 成功事件处理
        event_bus.subscribe(EventTypes.SUCCESS_EVENT, self._handle_success_event)

        # 系统事件处理
        event_bus.subscribe(EventTypes.SYSTEM_EVENT, self._handle_system_event)

    def _handle_error_event(self, event_data: Dict[str, Any]) -> None:
        """
        处理错误事件

        Args:
            event_data: 事件数据
        """
        if 'message' in event_data:
            logger.error(event_data['message'])

            # 如果通知管理器已初始化，发送通知
            if self.services_initialized:
                notifier_manager.send_notification(event_data['message'], "error")

    def _handle_warning_event(self, event_data: Dict[str, Any]) -> None:
        """
        处理警告事件

        Args:
            event_data: 事件数据
        """
        if 'message' in event_data:
            logger.warning(event_data['message'])

            # 如果通知管理器已初始化，发送通知
            if self.services_initialized:
                notifier_manager.send_notification(event_data['message'], "warning")

    def _handle_success_event(self, event_data: Dict[str, Any]) -> None:
        """
        处理成功事件

        Args:
            event_data: 事件数据
        """
        if 'message' in event_data:
            logger.info(event_data['message'])

            # 如果通知管理器已初始化，发送通知
            if self.services_initialized:
                notifier_manager.send_notification(event_data['message'], "info")

    def _handle_system_event(self, event_data: Dict[str, Any]) -> None:
        """
        处理系统事件

        Args:
            event_data: 事件数据
        """
        if 'message' in event_data:
            logger.info(event_data['message'])

    def _watch_services(self) -> None:
        """
        监控服务状态
        """
        logger.info("服务状态监控线程已启动")

        while not self.stop_requested:
            try:
                # 检查各服务状态
                notifier_status = notifier_manager.get_status()
                backup_status = backup_manager.get_status()
                monitor_status = monitor_manager.get_status()
                heartbeat_status = heartbeat_service.get_status()

                # 检查是否有服务需要重启
                if (self.services_started and
                    (not notifier_status['running'] or
                     not backup_status['running'] or
                     not monitor_status['running'] or
                     not heartbeat_status['running'])):

                    logger.warning("检测到服务异常，尝试重新启动")

                    if not notifier_status['running']:
                        notifier_manager.start()

                    if not backup_status['running']:
                        backup_manager.start()

                    if not monitor_status['running']:
                        monitor_manager.start()

                    if not heartbeat_status['running']:
                        heartbeat_service.start()

                # 每5秒检查一次
                time.sleep(5)

            except Exception as e:
                logger.error(f"服务状态监控异常: {str(e)}")
                logger.error(traceback.format_exc())
                time.sleep(10)  # 异常情况下，稍微延长检查间隔

# 创建单例实例
service_manager = ServiceManager()