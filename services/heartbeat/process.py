import os
import time
import subprocess
from typing import Dict, Any, Optional, List, Tuple

from core.heartbeat.base import HeartbeatBase
from config.base import ConfigBase
from utils.logger import get_logger
from utils.system import run_shell_script, run_shell_command
from utils.events import get_event_bus, EventTypes

logger = get_logger()
event_bus = get_event_bus()

class ProcessHeartbeat(HeartbeatBase):
    """
    进程心跳监控，检测进程是否存在，如果不存在则重启
    """
    
    def __init__(self, process_name: str, restart_cmd: str, check_interval: int = 60):
        """
        初始化进程心跳监控
        
        Args:
            process_name: 进程名称
            restart_cmd: 重启命令
            check_interval: 检查间隔（秒）
        """
        self.process_name = process_name
        self.restart_cmd = restart_cmd
        self.check_interval = check_interval
        self.last_check_time = 0
        self.last_status = False
        self.failure_count = 0
        self.max_failures = 3
        self.is_running = False
    
    def check(self) -> Tuple[bool, str]:
        """
        检查进程是否存在
        
        Returns:
            Tuple[bool, str]: 进程是否存在和消息
        """
        current_time = time.time()
        
        # 如果距离上次检查时间不足间隔时间，则返回上次结果
        if current_time - self.last_check_time < self.check_interval:
            return self.last_status, f"使用缓存结果, 进程: {self.process_name}, 状态: {'存在' if self.last_status else '不存在'}"
        
        self.last_check_time = current_time
        
        # 检查进程是否存在
        code, stdout, _ = run_shell_command(f"pgrep -f {self.process_name}")
        
        if code == 0 and stdout.strip():
            self.last_status = True
            self.failure_count = 0
            return True, f"进程存在: {self.process_name}"
        else:
            self.last_status = False
            self.failure_count += 1
            return False, f"进程不存在: {self.process_name}"
    
    def handle_failure(self) -> bool:
        """
        处理进程不存在的情况，尝试重启进程
        
        Returns:
            bool: 处理是否成功
        """
        if self.failure_count > self.max_failures:
            logger.error(f"进程 {self.process_name} 连续失败次数超过阈值 {self.max_failures}，不再尝试重启")
            event_bus.publish(EventTypes.ERROR_EVENT, 
                             message=f"进程 {self.process_name} 连续失败次数超过阈值，不再尝试重启")
            return False
        
        logger.info(f"尝试重启进程: {self.process_name}")
        event_bus.publish(EventTypes.SYSTEM_EVENT, 
                         message=f"尝试重启进程: {self.process_name}")
        
        try:
            # 执行重启命令
            subprocess.run(self.restart_cmd, shell=True, check=True)
            
            # 等待一段时间，然后再次检查
            time.sleep(5)
            
            # 再次检查进程是否存在
            is_running, message = self.check()
            
            if is_running:
                logger.info(f"进程重启成功: {self.process_name}")
                event_bus.publish(EventTypes.SUCCESS_EVENT, 
                                 message=f"进程重启成功: {self.process_name}")
                return True
            else:
                logger.error(f"进程重启失败: {self.process_name}")
                event_bus.publish(EventTypes.ERROR_EVENT, 
                                 message=f"进程重启失败: {self.process_name}")
                return False
                
        except Exception as e:
            logger.error(f"重启进程 {self.process_name} 时出错: {str(e)}")
            event_bus.publish(EventTypes.ERROR_EVENT, 
                             message=f"重启进程 {self.process_name} 时出错: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取心跳状态
        
        Returns:
            Dict[str, Any]: 心跳状态信息
        """
        is_running, _ = self.check()
        
        return {
            'type': 'process',
            'name': self.process_name,
            'running': is_running,
            'failure_count': self.failure_count,
            'last_check_time': self.last_check_time
        }

class DashboardHeartbeat(ProcessHeartbeat):
    """
    哪吒面板的心跳监控
    """
    
    def __init__(self, check_interval: int = 60):
        """
        初始化哪吒面板心跳监控
        
        Args:
            check_interval: 检查间隔（秒）
        """
        super().__init__('nezha-dashboard', 
                        "cd ~ && ./heart_beat_entry.sh 0|$(hostname)|22|$(whoami)",
                        check_interval)

class AgentHeartbeat(ProcessHeartbeat):
    """
    哪吒Agent的心跳监控
    """
    
    def __init__(self, check_interval: int = 60):
        """
        初始化哪吒Agent心跳监控
        
        Args:
            check_interval: 检查间隔（秒）
        """
        super().__init__('nezha-agent', 
                        "cd ~ && ./heart_beat_entry.sh 0|$(hostname)|22|$(whoami)",
                        check_interval)
