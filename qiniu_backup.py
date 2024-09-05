import os
import requests
from datetime import datetime
from typing import Dict
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry
from qiniu import Auth, put_file
import qiniu.config

class QiniuBack:
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
        self.sys_config_entry = sys_config_entry
        self.logger = LoggerWrapper()
        self.access_key = self.sys_config_entry.get("QINIU_ACCESS_KEY")
        self.secret_key = self.sys_config_entry.get("QINIU_SECRET_KEY")
        self.bucket_name = self.sys_config_entry.get("QINIU_BUCKET_NAME")
        self.dir_name = self.sys_config_entry.get("QINIU_DIR_NAME")
        self.ttl = int(self.sys_config_entry.get("QINIU_EXPIRE_HOUR", 1)) * 3600
        self.auth = Auth(self.access_key, self.secret_key)

    def backup_bashboard_db(self, db_file: str):
        try:
            now = datetime.now()
            date_prefix = now.strftime('%d_%H_%M')
            month_dir = now.strftime('%Y%m')
            
            file_name = os.path.basename(db_file)
            new_file_name = f"{date_prefix}_{file_name}"
            upload_path = f"{self.dir_name}/{month_dir}/{new_file_name}"
            
            token = self.auth.upload_token(self.bucket_name, upload_path, self.ttl)
            
            ret, info = put_file(token, upload_path, db_file)

            if info.status_code == 200:
                self.logger.info(f"====> 上传到七牛成功 bucket_name={self.bucket_name} {upload_path}")
                return f"{self.bucket_name}/{upload_path}"
            else:
                self.logger.error(f"====> 上传到七牛失败 bucket_name={self.bucket_name} {upload_path} 错误信息: {info}")
                return None
        except Exception as e:
            self.logger.error(f"====> 上传到七牛失败 bucket_name={self.bucket_name} {upload_path} 错误：{str(e)}")
            return None
