import time
import threading
from typing import Dict, Any, Optional, List, Tuple

from services.monitor.base import MonitorBase
from core.monitor.process import ProcessMonitor, DashboardMonitor, AgentMonitor
from core.monitor.url import UrlMonitor
from config.base import ConfigBase
from utils.logger import get_logger
from utils.events import get_event_bus, EventTypes
from utils.decorators import singleton

logger = get_logger()
event_bus = get_event_bus()

@singleton
class MonitorManager:
    """
    监控管理器，管理多种监控
    """

    def __init__(self):
        self.monitors = {}
        self.config = None
        self.running = False
        self.thread = None
        self.stop_requested = False

    def initialize(self, config: ConfigBase) -> bool:
        """
        初始化监控管理器

        Args:
            config: 配置对象

        Returns:
            bool: 初始化是否成功
        """
        self.config = config

        # 创建默认监控
        self.monitors['dashboard'] = DashboardMonitor()
        self.monitors['agent'] = AgentMonitor()

        # 添加自定义监控
        self._add_custom_monitors()

        logger.info("监控管理器初始化完成")
        return True

    def _add_custom_monitors(self) -> None:
        """
        添加自定义监控
        """
        if not self.config:
            return

        # 获取监控配置
        monitor_config = self.config.get('monitor', {})

        # 添加进程监控
        processes = monitor_config.get('processes', [])
        for process in processes:
            if 'name' in process:
                name = process['name']
                expected_count = process.get('expected_count', 1)
                check_interval = process.get('check_interval', 300)

                self.monitors[f"process_{name}"] = ProcessMonitor(
                    name, expected_count, check_interval)

        # 添加URL监控
        urls = monitor_config.get('urls', [])
        for url_config in urls:
            if 'url' in url_config:
                url = url_config['url']
                expected_status = url_config.get('expected_status', 200)
                check_interval = url_config.get('check_interval', 300)

                self.monitors[f"url_{url}"] = UrlMonitor(
                    url, expected_status, check_interval)

    def start(self) -> bool:
        """
        启动监控服务

        Returns:
            bool: 启动是否成功
        """
        if self.running:
            logger.warning("监控服务已经在运行")
            return True

        self.stop_requested = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        self.running = True
        logger.info("监控服务已启动")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="监控服务已启动")

        return True

    def stop(self) -> bool:
        """
        停止监控服务

        Returns:
            bool: 停止是否成功
        """
        if not self.running:
            logger.warning("监控服务未在运行")
            return True

        self.stop_requested = True
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        self.running = False
        logger.info("监控服务已停止")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="监控服务已停止")

        return True

    def _run(self) -> None:
        """
        监控服务运行循环
        """
        logger.info("监控服务线程已启动")

        while not self.stop_requested:
            try:
                # 遍历所有监控，执行检查
                for name, monitor in self.monitors.items():
                    is_ok, message, _ = monitor.check()

                    # 记录异常情况，但正常情况不记录，以减少日志量
                    if not is_ok:
                        logger.warning(f"监控异常: {name}, {message}")

                # 每30秒检查一次
                time.sleep(30)

            except Exception as e:
                logger.error(f"监控服务运行错误: {str(e)}")
                time.sleep(60)  # 发生错误时，稍微延长检查间隔

    def get_status(self) -> Dict[str, Any]:
        """
        获取监控服务状态

        Returns:
            Dict[str, Any]: 监控服务状态信息
        """
        result = {
            'running': self.running,
            'monitors': {}
        }

        for name, monitor in self.monitors.items():
            result['monitors'][name] = monitor.get_metrics()

        return result

    def add_monitor(self, name: str, monitor: MonitorBase) -> bool:
        """
        添加监控

        Args:
            name: 监控名称
            monitor: 监控对象

        Returns:
            bool: 添加是否成功
        """
        if name in self.monitors:
            logger.warning(f"监控 {name} 已存在，将被覆盖")

        self.monitors[name] = monitor
        logger.info(f"添加监控: {name}")

        return True

    def remove_monitor(self, name: str) -> bool:
        """
        移除监控

        Args:
            name: 监控名称

        Returns:
            bool: 移除是否成功
        """
        if name not in self.monitors:
            logger.warning(f"监控 {name} 不存在")
            return False

        del self.monitors[name]
        logger.info(f"移除监控: {name}")

        return True

    def get_monitor(self, name: str) -> Optional[MonitorBase]:
        """
        获取监控

        Args:
            name: 监控名称

        Returns:
            Optional[MonitorBase]: 监控对象，如果不存在则返回None
        """
        return self.monitors.get(name)

# 创建单例实例
monitor_manager = MonitorManager()
