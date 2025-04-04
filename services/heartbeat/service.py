import time
import threading
from typing import Dict, Any, Optional, List, Tuple

from services.heartbeat.base import HeartbeatBase
from services.heartbeat.process import DashboardHeartbeat, AgentHeartbeat
from config.base import ConfigBase
from utils.logger import get_logger
from utils.events import get_event_bus, EventTypes

logger = get_logger()
event_bus = get_event_bus()

class HeartbeatService:
    """
    心跳服务，负责监控和保活
    """

    def __init__(self):
        """
        初始化心跳服务
        """
        self.heartbeats = {}
        self.config = None
        self.running = False
        self.thread = None
        self.stop_requested = False
        self._lock = threading.RLock()  # 添加线程锁

    def initialize(self, config: ConfigBase) -> bool:
        """
        初始化心跳服务

        Args:
            config: 配置对象

        Returns:
            bool: 初始化是否成功
        """
        self.config = config

        # 创建心跳监控
        self.heartbeats['dashboard'] = DashboardHeartbeat()
        self.heartbeats['agent'] = AgentHeartbeat()

        # 添加自定义心跳监控
        self._add_custom_heartbeats()

        return True

    def _add_custom_heartbeats(self) -> None:
        """
        添加自定义心跳监控
        """
        if not self.config:
            return

        # 获取心跳配置
        heartbeat_config = self.config.get('heartbeat', {})

        # 添加自定义进程心跳监控
        processes = heartbeat_config.get('processes', [])
        for process in processes:
            if 'name' in process and 'restart_cmd' in process:
                name = process['name']
                restart_cmd = process['restart_cmd']
                check_interval = process.get('check_interval', 60)

                self.heartbeats[f"process_{name}"] = ProcessHeartbeat(
                    name, restart_cmd, check_interval)

    def start(self) -> bool:
        """
        启动心跳服务

        Returns:
            bool: 启动是否成功
        """
        if self.running:
            logger.warning("心跳服务已经在运行")
            return True

        self.stop_requested = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        self.running = True
        logger.info("心跳服务已启动")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="心跳服务已启动")

        return True

    def stop(self) -> bool:
        """
        停止心跳服务

        Returns:
            bool: 停止是否成功
        """
        if not self.running:
            logger.warning("心跳服务未在运行")
            return True

        self.stop_requested = True
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        self.running = False
        logger.info("心跳服务已停止")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="心跳服务已停止")

        return True

    def _run(self) -> None:
        """
        心跳服务运行循环
        """
        logger.info("心跳服务线程已启动")

        while not self.stop_requested:
            try:
                # 创建心跳监控的副本，避免遍历时修改
                with self._lock:
                    heartbeats_copy = dict(self.heartbeats)

                # 遍历所有心跳监控，执行检查
                for name, heartbeat in heartbeats_copy.items():
                    if self.stop_requested:
                        break

                    try:
                        is_running, message = heartbeat.check()

                        if not is_running:
                            logger.warning(f"心跳检测失败: {name}, {message}")
                            # 处理失败
                            heartbeat.handle_failure()
                    except Exception as e:
                        logger.error(f"心跳检查错误: {name}, 错误: {str(e)}")

                # 每10秒检查一次
                time.sleep(10)

            except Exception as e:
                logger.error(f"心跳服务运行错误: {str(e)}")
                time.sleep(30)  # 发生错误时，稍微延长检查间隔

    def add_heartbeat(self, name: str, heartbeat: HeartbeatBase) -> None:
        """
        添加心跳监控

        Args:
            name: 心跳监控名称
            heartbeat: 心跳监控实例
        """
        with self._lock:
            self.heartbeats[name] = heartbeat
            logger.info(f"添加心跳监控: {name}")

    def remove_heartbeat(self, name: str) -> None:
        """
        移除心跳监控

        Args:
            name: 心跳监控名称
        """
        with self._lock:
            if name in self.heartbeats:
                del self.heartbeats[name]
                logger.info(f"移除心跳监控: {name}")

    def get_status(self) -> Dict[str, Any]:
        """
        获取心跳服务状态

        Returns:
            Dict[str, Any]: 心跳服务状态信息
        """
        with self._lock:
            result = {
                'running': self.running,
                'heartbeats': {}
            }

            for name, heartbeat in self.heartbeats.items():
                result['heartbeats'][name] = heartbeat.get_status()

        return result

# 创建单例实例
heartbeat_service = HeartbeatService()
