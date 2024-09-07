import os
from datetime import datetime
from typing import Dict, Optional
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry
import oss2

class AliOssBackup:
    _instance = None
    DATE_FORMAT = '%d_%H_%M'
    MONTH_FORMAT = '%Y%m'

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
        self.access_key_id = self.sys_config_entry.get("ALI_OSS_ACCESS_KEY_ID")
        self.access_key_secret = self.sys_config_entry.get("ALI_OSS_ACCESS_KEY_SECRET")
        self.endpoint = self.sys_config_entry.get("ALI_OSS_ENDPOINT")
        self.bucket_name = self.sys_config_entry.get("ALI_OSS_BUCKET_NAME")
        self.dir_name = self.sys_config_entry.get("ALI_OSS_DIR_NAME")
        self.ttl = int(self.sys_config_entry.get("ALI_OSS_EXPIRE_DAYS", 7)) * 24 * 3600
        
        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

    def backup_dashboard_db(self, db_file: str) -> Optional[str]:
        try:
            now = datetime.now()
            date_prefix = now.strftime(self.DATE_FORMAT)
            month_dir = now.strftime(self.MONTH_FORMAT)
            
            file_name = os.path.basename(db_file)
            new_file_name = f"{date_prefix}_{file_name}"
            key = f"{self.dir_name}/{month_dir}/{new_file_name}"
            
            with open(db_file, 'rb') as file_obj:
                result = self.bucket.put_object(key, file_obj)
            
            if result.status == 200:
                self.logger.info(f"====> 上传到阿里云成功 bucket_name={self.bucket_name} {key}")
                return f"{self.bucket_name}/{key}"
            else:
                self.logger.error(f"====> 上传到阿里云失败 bucket_name={self.bucket_name} {key} 状态码: {result.status}")
                return None
        except Exception as e:
            self.logger.error(f"====> 上传到阿里云失败 bucket_name={self.bucket_name} {key} 错误：{str(e)}")
            return None
