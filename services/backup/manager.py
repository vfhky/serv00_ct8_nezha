import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from services.backup.factory import BackupFactory
from config.base import ConfigBase
from utils.logger import get_logger
from utils.events import get_event_bus, EventTypes

logger = get_logger()
event_bus = get_event_bus()

class BackupManager:
    """
    备份管理器，用于统一管理备份操作
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackupManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        self._initialized = True
        self.config = None
    
    def initialize(self, config: ConfigBase) -> None:
        """
        初始化备份管理器
        
        Args:
            config: 配置实例
        """
        self.config = config
        # 创建所有备份实现
        BackupFactory.create_backups(config)
    
    def backup_file(self, file_path: str, target_path: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        备份文件
        
        Args:
            file_path: 文件路径
            target_path: 目标路径，可选
            
        Returns:
            Dict[str, Optional[str]]: 备份结果，键为备份服务名称，值为备份路径
        """
        if not os.path.exists(file_path):
            logger.error(f"备份文件不存在: {file_path}")
            event_bus.publish(EventTypes.BACKUP_FAILED, file_path=file_path, error="文件不存在")
            return {}
        
        logger.info(f"开始备份文件: {file_path}")
        event_bus.publish(EventTypes.BACKUP_STARTED, file_path=file_path)
        
        results = BackupFactory.backup_all(file_path, target_path)
        
        success_count = sum(1 for result in results.values() if result is not None)
        total_count = len(results)
        
        if success_count > 0:
            logger.info(f"文件备份完成: {file_path}, 成功: {success_count}/{total_count}")
            event_bus.publish(EventTypes.BACKUP_COMPLETED, file_path=file_path, results=results)
        else:
            logger.error(f"文件备份失败: {file_path}, 成功: 0/{total_count}")
            event_bus.publish(EventTypes.BACKUP_FAILED, file_path=file_path, error="所有备份服务都失败了")
        
        return results
    
    def backup_dashboard_db(self, db_file: str) -> Dict[str, Optional[str]]:
        """
        备份仪表盘数据库
        
        Args:
            db_file: 数据库文件路径
            
        Returns:
            Dict[str, Optional[str]]: 备份结果
        """
        logger.info(f"开始备份仪表盘数据库: {db_file}")
        
        return self.backup_file(db_file)
    
    def schedule_backup(self, file_path: str, interval_hours: int = 24) -> None:
        """
        计划备份任务
        
        Args:
            file_path: 文件路径
            interval_hours: 备份间隔（小时）
        """
        logger.info(f"计划备份任务: {file_path}, 间隔: {interval_hours}小时")
        # 注意: 这里只是占位，实际上计划任务应该由定时任务系统处理
    
    def get_backup_services_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取备份服务状态
        
        Returns:
            Dict[str, Dict[str, Any]]: 备份服务状态
        """
        backups = BackupFactory.get_enabled_backups()
        
        status = {}
        for backup in backups:
            class_name = backup.__class__.__name__
            status[class_name] = {
                "enabled": backup.is_enabled(),
                "type": class_name,
                "bucket": getattr(backup, "bucket_name", None),
                "ttl": getattr(backup, "ttl", None)
            }
        
        return status

# 创建单例实例
backup_manager = BackupManager()
