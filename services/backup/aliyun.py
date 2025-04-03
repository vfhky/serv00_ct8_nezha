import os
from datetime import datetime
from typing import Optional, Dict
import oss2
from services.backup.base import BackupBase
from services.backup.factory import BackupFactory
from config.base import ConfigBase
from utils.logger import get_logger

logger = get_logger()

class AliyunOssBackup(BackupBase):
    """
    阿里云OSS备份实现
    """
    _instance = None
    DATE_FORMAT = '%d'
    MONTH_FORMAT = '%Y%m'
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AliyunOssBackup, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        self._initialized = True
        self.enabled = False
        self.access_key_id = None
        self.access_key_secret = None
        self.endpoint = None
        self.bucket_name = None
        self.dir_name = None
        self.ttl = 7
        self.auth = None
        self.bucket = None
    
    @classmethod
    def initialize(cls, config: ConfigBase) -> 'AliyunOssBackup':
        """
        初始化备份实例
        
        Args:
            config: 配置实例
            
        Returns:
            AliyunOssBackup: 备份实例
        """
        instance = cls()
        instance.enabled = config.get('ENABLE_ALI_OSS_BACKUP') == '1'
        instance.access_key_id = config.get('ALI_OSS_ACCESS_KEY_ID')
        instance.access_key_secret = config.get('ALI_OSS_ACCESS_KEY_SECRET')
        instance.endpoint = config.get('ALI_OSS_ENDPOINT')
        instance.bucket_name = config.get('ALI_OSS_BUCKET_NAME')
        instance.dir_name = config.get('ALI_OSS_DIR_NAME')
        
        try:
            instance.ttl = int(config.get('ALI_OSS_EXPIRE_DAYS', 7))
        except (ValueError, TypeError):
            instance.ttl = 7
        
        if instance.enabled:
            if not instance.access_key_id or not instance.access_key_secret:
                logger.warning("阿里云OSS备份已启用，但未配置访问密钥")
                instance.enabled = False
            elif not instance.endpoint or not instance.bucket_name:
                logger.warning("阿里云OSS备份已启用，但未配置端点或存储桶名称")
                instance.enabled = False
            else:
                # 初始化阿里云OSS客户端
                instance.auth = oss2.Auth(instance.access_key_id, instance.access_key_secret)
                instance.bucket = oss2.Bucket(instance.auth, instance.endpoint, instance.bucket_name)
        
        # 注册到工厂
        BackupFactory.register_backup('aliyun', instance)
        
        return instance
    
    def is_enabled(self) -> bool:
        """
        检查备份服务是否启用
        
        Returns:
            bool: 服务是否启用
        """
        return (self.enabled and self.access_key_id is not None and 
                self.access_key_secret is not None and self.bucket_name is not None and
                self.bucket is not None)
    
    def ensure_backup_environment(self) -> bool:
        """
        确保备份环境已准备就绪
        
        Returns:
            bool: 环境是否准备就绪
        """
        if not self.is_enabled():
            return False
        
        try:
            self._ensure_bucket_exists()
            self._set_lifecycle_rule()
            return True
        except Exception as e:
            logger.error(f"确保阿里云OSS备份环境就绪失败: {str(e)}")
            return False
    
    def _ensure_bucket_exists(self) -> None:
        """
        确保存储桶存在
        """
        try:
            self.bucket.get_bucket_info()
            logger.info(f"====> 阿里云OSS bucket: {self.bucket_name} 已经存在")
        except oss2.exceptions.NoSuchBucket:
            try:
                self.bucket.create_bucket()
                logger.info(f"====> 阿里云OSS创建bucket: {self.bucket_name} 成功")
            except Exception as e:
                logger.error(f"====> 阿里云OSS创建bucket: {self.bucket_name} 失败: {str(e)}")
                raise
    
    def _set_lifecycle_rule(self) -> None:
        """
        设置生命周期规则
        """
        try:
            rule = oss2.models.LifecycleRule(
                rule_id='delete-after-days',
                prefix=self.dir_name,
                status='Enabled',
                expiration=oss2.models.LifecycleExpiration(days=self.ttl)
            )
            
            self.bucket.put_bucket_lifecycle([rule])
            logger.info(f"====> 阿里云OSS设置生命周期规则成功: bucket={self.bucket_name}, ttl={self.ttl}")
        except Exception as e:
            logger.error(f"====> 阿里云OSS设置生命周期规则失败: {str(e)}")
            raise
    
    def backup(self, source_file: str, target_path: Optional[str] = None) -> Optional[str]:
        """
        备份文件
        
        Args:
            source_file: 源文件路径
            target_path: 目标路径，可选
            
        Returns:
            Optional[str]: 备份文件的路径，如果备份失败则返回None
        """
        if not self.is_enabled():
            logger.warning("阿里云OSS备份未启用")
            return None
        
        if not os.path.exists(source_file):
            logger.error(f"备份文件不存在: {source_file}")
            return None
        
        try:
            # 确保环境就绪
            self.ensure_backup_environment()
            
            # 生成目标路径
            now = datetime.now()
            date_prefix = now.strftime(self.DATE_FORMAT)
            month_dir = now.strftime(self.MONTH_FORMAT)
            
            file_name = os.path.basename(source_file)
            new_file_name = f"{date_prefix}_{file_name}"
            key = f"{self.dir_name}/{month_dir}/{new_file_name}" if self.dir_name else f"{month_dir}/{new_file_name}"
            
            if target_path:
                key = target_path
            
            # 上传文件
            result = self.bucket.put_object_from_file(key, source_file)
            
            if result.status == 200:
                logger.info(f"====> 阿里云OSS备份成功: {source_file} -> {self.bucket_name}/{key}")
                return f"{self.bucket_name}/{key}"
            else:
                logger.error(f"====> 阿里云OSS备份失败: {source_file}, 状态码: {result.status}")
                return None
        except Exception as e:
            logger.error(f"====> 阿里云OSS备份异常: {source_file}, 错误: {str(e)}")
            return None

# 创建实例并注册
aliyun_backup = AliyunOssBackup()
