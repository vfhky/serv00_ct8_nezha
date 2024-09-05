#!/usr/bin/env python3
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry
from qiniu_backup import QiniuBack

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
        self.qiniu_backup = QiniuBack(self.sys_config_entry) if self.sys_config_entry.get("ENABLE_QINIU_BACKUP") == "1" else None

    def backup_bashboard_db(self, db_file: str, e: Exception):
        self._backup_bashboard_db("backup_bashboard_db", db_file=db_file, e=e)

    def _backup_bashboard_db(self, method_name: str, **kwargs):
        if self.qiniu_backup:
            getattr(self.qiniu_backup, method_name)(**kwargs)
