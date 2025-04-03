"""
服务模块包含所有功能服务实现，包括：
- notification: 通知服务
- backup: 备份服务
- ssh: SSH服务
- monitor: 监控服务
- heartbeat: 心跳服务
- installer: 安装服务
"""

from services.notification.manager import notifier_manager
from services.backup.manager import backup_manager
from services.ssh.helper import ssh_helper
from services.monitor.manager import monitor_manager
from services.heartbeat.service import heartbeat_service
from services.installer.manager import installation_manager

__all__ = [
    'notifier_manager',
    'backup_manager',
    'ssh_helper',
    'monitor_manager',
    'heartbeat_service',
    'installation_manager'
]
