import os
from datetime import datetime
from typing import Optional
from logger_wrapper import LoggerWrapper
from sys_config_entry import SysConfigEntry
from qiniu import Auth, put_file, BucketManager
import qiniu.config

class QiniuBackup:
    _instance = None
    DATE_FORMAT = '%d_%H_%M'
    MONTH_FORMAT = '%Y%m'
    PRIVATE = "1"
    PUBLIC = "0"
    
    def __new__(cls, sys_config_entry: SysConfigEntry):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, sys_config_entry: SysConfigEntry):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.sys_config_entry = sys_config_entry
        self.logger = LoggerWrapper()
        self.access_key = self.sys_config_entry.get("QINIU_ACCESS_KEY")
        self.secret_key = self.sys_config_entry.get("QINIU_SECRET_KEY")
        self.region = self.sys_config_entry.get("QINIU_REGION")
        self.bucket_name = self.sys_config_entry.get("QINIU_BUCKET_NAME")
        self.dir_name = self.sys_config_entry.get("QINIU_DIR_NAME")
        self.ttl = str(self.sys_config_entry.get("QINIU_EXPIRE_DAYS", 7))
        self.auth = Auth(self.access_key, self.secret_key)
        self.bucket_manager = BucketManager(self.auth)

    def _ensure_bucket_exists(self):
        try:
            buckets, _ = self.bucket_manager.list_bucket(self.region)
            buckets = buckets or []
            bucket_ids = [bucket['id'] for bucket in buckets]
            if not bucket_ids or self.bucket_name not in bucket_ids:
                self._create_bucket()
            else:
                self.logger.info(f"====> 七牛 Bucket 已存在: {self.bucket_name}")
        except Exception as e:
            self.logger.error(f"====> 七牛检查或创建 bucket: {self.bucket_name} 时出错: {str(e)}")
            raise

    def _create_bucket(self):
        try:
            ret, info = self.bucket_manager.mkbucketv3(self.bucket_name, self.region)
            if info.status_code == 200:
                self.logger.info(f"====> 七牛成功创建 Bucket: {self.bucket_name}")
                self._change_bucket_permission(self.PRIVATE)
            else:
                self.logger.error(f"====> 七牛创建 Bucket 失败: {self.bucket_name}, 错误信息: {info}")
                raise Exception(f"创建 bucket 失败: {info}")
        except Exception as e:
            self.logger.error(f"====> 七牛创建 bucket: {self.bucket_name} 时出错: {str(e)}")
            raise

    def _change_bucket_permission(self, private: str):
        try:
            if private not in (self.PRIVATE, self.PUBLIC):
                raise ValueError("无效的权限参数")
            private_desc = "私有" if private == self.PRIVATE else "公有"
            ret, info = self.bucket_manager.change_bucket_permission(self.bucket_name, private)
            if info.status_code == 200:
                self.logger.info(f"====> 七牛设置 Bucket: {self.bucket_name} {private_desc} 属性成功")
            else:
                self.logger.error(f"====> 七牛设置 Bucket: {self.bucket_name} {private_desc} 属性失败, 错误信息: {info}")
        except Exception as e:
            self.logger.error(f"====> 七牛设置 bucket: {self.bucket_name} {private_desc} 属性时出错: {str(e)}")
            raise

    def _set_file_expiry(self, upload_path: str):
        try:
            ret, info = self.bucket_manager.delete_after_days(self.bucket_name, upload_path, self.ttl)
            if info.status_code == 200:
                self.logger.info(f"====> 七牛成功设置文件 {upload_path} 的过期时间为 {self.ttl} 天")
            else:
                self.logger.error(f"====> 七牛设置文件 {upload_path} 的过期时间失败: {info}")
        except Exception as e:
            self.logger.error(f"====> 七牛设置文件 {upload_path} 的过期时间时出错: {str(e)}")

    def backup_dashboard_db(self, db_file: str) -> Optional[str]:
        try:
            self._ensure_bucket_exists()
            now = datetime.now()
            date_prefix = now.strftime(self.DATE_FORMAT)
            month_dir = now.strftime(self.MONTH_FORMAT)
            
            file_name = os.path.basename(db_file)
            new_file_name = f"{date_prefix}_{file_name}"
            upload_path = f"{self.dir_name}/{month_dir}/{new_file_name}"
            
            token = self.auth.upload_token(self.bucket_name, upload_path, 3600)
            
            ret, info = put_file(token, upload_path, db_file)
            if info.status_code == 200:
                self.logger.info(f"====> 七牛: [{db_file}] 上传成功 bucket_name={self.bucket_name} {upload_path}")
                
                self._set_file_expiry(upload_path)
                
                return f"{self.bucket_name}/{upload_path}"
            else:
                self.logger.error(f"====> 七牛: [{db_file}] 上传失败 bucket_name={self.bucket_name} {upload_path} 详情: {info}")
                return None
        except Exception as e:
            self.logger.error(f"====> 七牛: [{db_file}] 上传失败 bucket_name={self.bucket_name} {upload_path} 错误：{str(e)}")
            return None
