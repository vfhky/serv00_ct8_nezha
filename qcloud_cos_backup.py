import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry
from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError, CosClientError

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
        self.app_id = self.sys_config_entry.get("QCLOUD_COS_APP_ID")
        self.secret_id = self.sys_config_entry.get("QCLOUD_COS_SECRET_ID")
        self.secret_key = self.sys_config_entry.get("QCLOUD_COS_SECRET_KEY")
        self.region = self.sys_config_entry.get("QCLOUD_COS_REGION")
        self.bucket_name = f"{self.sys_config_entry.get('QCLOUD_COS_BUCKET_NAME')}-{self.app_id}"
        self.dir_name = self.sys_config_entry.get("QCLOUD_COS_DIR_NAME")
        self.ttl = int(self.sys_config_entry.get("QCLOUD_COS_EXPIRE_DAYS", 7))
        
        config = CosConfig(Region=self.region, SecretId=self.secret_id, SecretKey=self.secret_key)
        self.client = CosS3Client(config)

    def _ensure_bucket_exists(self):
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except CosServiceError as e:
            if e.get_status_code() == 404:
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    self.logger.info(f"腾讯云cos创建 Bucket 成功: {self.bucket_name}")
                except Exception as create_error:
                    self.logger.error(f"腾讯云cos创建 Bucket 失败: {self.bucket_name}, 错误: {str(create_error)}")
                    raise
            else:
                self.logger.error(f"腾讯云cos检查 Bucket 时出错: {self.bucket_name}, 错误: {str(e)}")
                raise

    def set_bucket_lifecycle(self):
        try:
            rule = {
                'ID': 'DeleteAfterDays',
                'Status': 'Enabled',
                'Filter': {'Prefix': self.dir_name},
                'Expiration': {'Days': self.ttl}
            }
            
            response = self.client.put_bucket_lifecycle(
                Bucket=self.bucket_name,
                LifecycleConfiguration={
                    'Rules': [rule]
                }
            )
            self.logger.info(f"腾讯云cos成功设置存储桶 {self.bucket_name} 的生命周期规则")
        except (CosServiceError, CosClientError) as e:
            self.logger.error(f"腾讯云cos设置存储桶 {self.bucket_name} 的生命周期规则失败：{str(e)}")

    def backup_dashboard_db(self, db_file: str) -> Optional[str]:
        key = None
        try:
            self._ensure_bucket_exists()
            self.set_bucket_lifecycle()
            
            now = datetime.now()
            date_prefix = now.strftime(self.DATE_FORMAT)
            month_dir = now.strftime(self.MONTH_FORMAT)
            
            file_name = os.path.basename(db_file)
            new_file_name = f"{date_prefix}_{file_name}"
            key = f"{self.dir_name}/{month_dir}/{new_file_name}"
           
            with open(db_file, 'rb') as fp:
                response = self.client.put_object(
                    Bucket=self.bucket_name,
                    Body=fp,
                    Key=key,
                    EnableMD5=True,
                    StorageClass='STANDARD'
                )
            
            if 'ETag' in response:
                self.logger.info(f"====> 上传到腾讯云cos成功 bucket_name={self.bucket_name} {key}")
                return f"{self.bucket_name}/{key}"
            else:
                self.logger.error(f"====> 上传到腾讯云cos失败 bucket_name={self.bucket_name} {key}")
                return None
        except (CosServiceError, CosClientError) as e:
            self.logger.error(f"====> 上传到腾讯云cos失败 bucket_name={self.bucket_name} {key} 错误：{str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"====> 上传到腾讯云cos失败 bucket_name={self.bucket_name} {key} 未知错误：{str(e)}")
            return None
