#!/usr/bin/env python3
import asyncio
from typing import List, Dict, Optional

from ..utils.logger_wrapper import LoggerWrapper
from ..config.sys_config_entry import SysConfigEntry
from ..utils.async_utils import AsyncExecutor
from .qiniu_backup import QiniuBackup
from .qcloud_cos_backup import QCloudCosBackup
from .ali_oss_backup import AliOssBackup

class BackupEntry:
    _instance = None

    def __new__(cls, sys_config_entry: SysConfigEntry):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, sys_config_entry: SysConfigEntry):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.logger = LoggerWrapper()
        self.sys_config_entry = sys_config_entry

        # 初始化所有备份系统
        self.backup_systems = []

        if self.sys_config_entry.get("ENABLE_QINIU_BACKUP") == "1":
            self.backup_systems.append(QiniuBackup(self.sys_config_entry))

        if self.sys_config_entry.get("ENABLE_QCLOUD_COS_BACKUP") == "1":
            self.backup_systems.append(QCloudCosBackup(self.sys_config_entry))

        if self.sys_config_entry.get("ENABLE_ALI_OSS_BACKUP") == "1":
            self.backup_systems.append(AliOssBackup(self.sys_config_entry))

    def backup_dashboard_db(self, db_file: str):
        """同步备份仪表盘数据库"""
        results = []
        for backup_system in self.backup_systems:
            try:
                result = backup_system.backup_dashboard_db(db_file)
                results.append((backup_system.__class__.__name__, result))
            except Exception as e:
                self.logger.error(f"备份系统 {backup_system.__class__.__name__} 备份失败: {str(e)}")
        return results

    async def backup_dashboard_db_async(self, db_file: str):
        """异步并行备份仪表盘数据库"""
        if not self.backup_systems:
            return []

        async def _backup_task(backup_system):
            try:
                result = await AsyncExecutor.run_in_thread(
                    backup_system.backup_dashboard_db,
                    db_file
                )
                return (backup_system.__class__.__name__, result)
            except Exception as e:
                self.logger.error(f"备份系统 {backup_system.__class__.__name__} 备份失败: {str(e)}")
                return (backup_system.__class__.__name__, None)

        tasks = [_backup_task(system) for system in self.backup_systems]
        return await asyncio.gather(*tasks)