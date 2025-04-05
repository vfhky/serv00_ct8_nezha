import os
import time
import subprocess
from typing import Dict, Any, Optional, List, Tuple

from services.monitor.base import MonitorBase
from config.base import ConfigBase
from utils.logger import get_logger
from utils.system import run_shell_script, run_shell_command
from utils.events import get_event_bus, EventTypes

logger = get_logger()
event_bus = get_event_bus()

class ProcessMonitor(MonitorBase):
    """
    进程监控，定期检查进程状态并报告
    """

    def __init__(self, process_name: str, expected_count: int = 1, check_interval: int = 300):
        """
        初始化进程监控

        Args:
            process_name: 进程名称
            expected_count: 预期进程数量
            check_interval: 检查间隔（秒）
        """
        self.process_name = process_name
        self.expected_count = expected_count
        self.check_interval = check_interval
        self.last_check_time = 0
        self.process_count = 0
        self.is_running = False
        self.last_details = {}
        self.last_message = ""

    def check_detailed(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检查进程状态，返回详细信息

        Returns:
            Tuple[bool, str, Dict[str, Any]]: 进程是否符合预期、消息和详细信息
        """
        current_time = time.time()

        # 如果距离上次检查时间不足间隔时间，则返回上次结果
        if current_time - self.last_check_time < self.check_interval:
            is_ok = self.process_count >= self.expected_count
            return is_ok, f"使用缓存结果, 进程: {self.process_name}, 数量: {self.process_count}", {
                'name': self.process_name,
                'count': self.process_count,
                'expected': self.expected_count,
                'last_check': self.last_check_time
            }

        self.last_check_time = current_time

        # 获取进程ID列表
        code, stdout, _ = run_shell_command(f"pgrep -f {self.process_name}")

        if code == 0 and stdout.strip():
            process_ids = stdout.strip().split('\n')
            self.process_count = len(process_ids)
            self.is_running = True
        else:
            self.process_count = 0
            self.is_running = False

        is_ok = self.process_count >= self.expected_count
        message = f"进程: {self.process_name}, 数量: {self.process_count}, 预期: {self.expected_count}"

        if not is_ok:
            logger.warning(f"进程监控异常: {message}")
            event_bus.publish(EventTypes.WARNING_EVENT, message=f"进程监控异常: {message}")

        self.last_message = message
        self.last_details = {
            'name': self.process_name,
            'count': self.process_count,
            'expected': self.expected_count,
            'last_check': self.last_check_time,
            'pid_list': process_ids if self.is_running else []
        }

        return is_ok, message, self.last_details

    def check(self) -> bool:
        """
        执行监控检查

        Returns:
            bool: 检查是否通过
        """
        is_ok, _, _ = self.check_detailed()
        return is_ok

    def handle_failure(self, error: Any) -> None:
        """
        处理监控失败的情况

        Args:
            error: 失败原因
        """
        logger.error(f"进程监控失败: {self.process_name}, 错误: {error}")
        event_bus.publish(EventTypes.ERROR_EVENT, message=f"进程监控失败: {self.process_name}, 错误: {error}")

    def get_status(self) -> Dict[str, Any]:
        """
        获取监控状态

        Returns:
            Dict[str, Any]: 监控状态的字典
        """
        return self.get_metrics()

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取监控指标

        Returns:
            Dict[str, Any]: 监控指标数据
        """
        _, _, details = self.check()

        # 如果进程不存在，返回基本信息
        if not self.is_running:
            return {
                'name': self.process_name,
                'count': 0,
                'running': False,
                'cpu_percent': 0,
                'memory_percent': 0,
                'uptime': 0
            }

        # 获取进程CPU和内存使用情况
        total_cpu = 0
        total_memory = 0
        for pid in details.get('pid_list', []):
            try:
                # 获取CPU使用率
                cpu_cmd = f"ps -p {pid} -o %cpu | tail -n 1"
                cpu_code, cpu_stdout, _ = run_shell_command(cpu_cmd)
                if cpu_code == 0 and cpu_stdout.strip():
                    total_cpu += float(cpu_stdout.strip())

                # 获取内存使用率
                mem_cmd = f"ps -p {pid} -o %mem | tail -n 1"
                mem_code, mem_stdout, _ = run_shell_command(mem_cmd)
                if mem_code == 0 and mem_stdout.strip():
                    total_memory += float(mem_stdout.strip())
            except:
                pass

        # 获取进程运行时间
        uptime = 0
        if details.get('pid_list'):
            try:
                oldest_pid = details['pid_list'][0]
                uptime_cmd = f"ps -p {oldest_pid} -o etimes | tail -n 1"
                uptime_code, uptime_stdout, _ = run_shell_command(uptime_cmd)
                if uptime_code == 0 and uptime_stdout.strip():
                    uptime = int(uptime_stdout.strip())
            except:
                pass

        return {
            'name': self.process_name,
            'count': self.process_count,
            'running': True,
            'cpu_percent': total_cpu,
            'memory_percent': total_memory,
            'uptime': uptime
        }

class DashboardMonitor(ProcessMonitor):
    """
    哪吒面板监控
    """

    def __init__(self, check_interval: int = 300):
        """
        初始化哪吒面板监控

        Args:
            check_interval: 检查间隔（秒）
        """
        super().__init__('nezha-dashboard', 1, check_interval)

    def get_status(self) -> Dict[str, Any]:
        """
        获取监控状态

        Returns:
            Dict[str, Any]: 监控状态的字典
        """
        return self.get_metrics()

    def handle_failure(self, error: Any) -> None:
        """
        处理监控失败的情况

        Args:
            error: 失败原因
        """
        logger.error(f"哪吒面板监控失败: {error}")
        event_bus.publish(EventTypes.ERROR_EVENT, message=f"哪吒面板监控失败: {error}")

class AgentMonitor(ProcessMonitor):
    """
    哪吒Agent监控
    """

    def __init__(self, check_interval: int = 300):
        """
        初始化哪吒Agent监控

        Args:
            check_interval: 检查间隔（秒）
        """
        super().__init__('nezha-agent', 1, check_interval)

    def get_status(self) -> Dict[str, Any]:
        """
        获取监控状态

        Returns:
            Dict[str, Any]: 监控状态的字典
        """
        return self.get_metrics()

    def handle_failure(self, error: Any) -> None:
        """
        处理监控失败的情况

        Args:
            error: 失败原因
        """
        logger.error(f"哪吒Agent监控失败: {error}")
        event_bus.publish(EventTypes.ERROR_EVENT, message=f"哪吒Agent监控失败: {error}")
