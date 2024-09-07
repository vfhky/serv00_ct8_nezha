import os
from datetime import datetime
from typing import Dict, Optional
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

class QCloudCosBackup:
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
        self.secret_id = self.sys_config_entry.get("QCLOUD_COS_SECRET_ID")
        self.secret_key = self.sys_config_entry.get("QCLOUD_COS_SECRET_KEY")
        self.region = self.sys_config_entry.get("QCLOUD_COS_REGION")
        self.bucket_name = self.sys_config_entry.get("QCLOUD_COS_BUCKET_NAME")
        self.dir_name = self.sys_config_entry.get("QCLOUD_COS_DIR_NAME")
        self.ttl = int(self.sys_config_entry.get("QCLOUD_COS_EXPIRE_DAYS", 7)) * 24 * 3600
        
        config = CosConfig(Region=self.region, SecretId=self.secret_id, SecretKey=self.secret_key)
        self.client = CosS3Client(config)

    def backup_dashboard_db(self, db_file: str) -> Optional[str]:
        try:
            now = datetime.now()
            date_prefix = now.strftime(self.DATE_FORMAT)
            month_dir = now.strftime(self.MONTH_FORMAT)
            
            file_name = os.path.basename(db_file)
            new_file_name = f"{date_prefix}_{file_name}"
            key = f"{self.dir_name}/{month_dir}/{new_file_name}"
            
            response = self.client.upload_file(
                Bucket=self.bucket_name,
                LocalFilePath=db_file,
                Key=key,
            )
            
            if response['ETag']:
                self.logger.info(f"====> 上传到腾讯云成功 bucket_name={self.bucket_name} {key}")
                return f"{self.bucket_name}/{key}"
            else:
                self.logger.error(f"====> 上传到腾讯云失败 bucket_name={self.bucket_name} {key}")
                return None
        except Exception as e:
            self.logger.error(f"====> 上传到腾讯云失败 bucket_name={self.bucket_name} {key} 错误：{str(e)}")
            return None
