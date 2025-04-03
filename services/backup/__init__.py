# This file is intentionally left empty to mark directory as Python package

from services.backup.base import BackupBase
from services.backup.factory import BackupFactory
from services.backup.manager import BackupManager, backup_manager
from services.backup.qiniu import QiniuBackup
from services.backup.tencent import TencentCosBackup
from services.backup.aliyun import AliyunOssBackup

# 导出工厂方法
backup_all = BackupFactory.backup_all
get_backup = BackupFactory.get_backup
create_backups = BackupFactory.create_backups
get_enabled_backups = BackupFactory.get_enabled_backups

# 导出管理器方法
initialize_backup = backup_manager.initialize
backup_file = backup_manager.backup_file
backup_dashboard_db = backup_manager.backup_dashboard_db

__all__ = [
    'BackupBase',
    'BackupFactory',
    'BackupManager',
    'backup_manager',
    'QiniuBackup',
    'TencentCosBackup',
    'AliyunOssBackup',
    'backup_all',
    'get_backup',
    'create_backups',
    'get_enabled_backups',
    'initialize_backup',
    'backup_file',
    'backup_dashboard_db'
]
