import os
from datetime import datetime
from typing import Optional
import qiniu
from qiniu import Auth, put_file, BucketManager
from services.backup.base import BackupBase
from services.backup.factory import BackupFactory
from config.base import ConfigBase
from utils.logger import get_logger

logger = get_logger()

class QiniuBackup(BackupBase):
    """
    七牛云备份实现
    """
    _instance = None
    DATE_FORMAT = '%d'
    MONTH_FORMAT = '%Y%m'
    PRIVATE = "1"
    PUBLIC = "0"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QiniuBackup, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        self._initialized = True
        self.enabled = False
        self.access_key = None
        self.secret_key = None
        self.region = None
        self.bucket_name = None
        self.dir_name = None
        self.ttl = 7
        self.auth = None
        self.bucket_manager = None
    
    @classmethod
    def initialize(cls, config: ConfigBase) -> 'QiniuBackup':
        """
        初始化备份实例
        
        Args:
            config: 配置实例
            
        Returns:
            QiniuBackup: 备份实例
        """
        instance = cls()
        instance.enabled = config.get('ENABLE_QINIU_BACKUP') == '1'
        instance.access_key = config.get('QINIU_ACCESS_KEY')
        instance.secret_key = config.get('QINIU_SECRET_KEY')
        instance.region = config.get('QINIU_REGION')
        instance.bucket_name = config.get('QINIU_BUCKET_NAME')
        instance.dir_name = config.get('QINIU_DIR_NAME')
        
        try:
            instance.ttl = int(config.get('QINIU_EXPIRE_DAYS', 7))
        except (ValueError, TypeError):
            instance.ttl = 7
        
        if instance.enabled:
            if not instance.access_key or not instance.secret_key:
                logger.warning("七牛云备份已启用，但未配置访问密钥")
                instance.enabled = False
            elif not instance.bucket_name:
                logger.warning("七牛云备份已启用，但未配置存储桶名称")
                instance.enabled = False
            else:
                # 初始化七牛云客户端
                instance.auth = Auth(instance.access_key, instance.secret_key)
                instance.bucket_manager = BucketManager(instance.auth)
        
        # 注册到工厂
        BackupFactory.register_backup('qiniu', instance)
        
        return instance
    
    def is_enabled(self) -> bool:
        """
        检查备份服务是否启用
        
        Returns:
            bool: 服务是否启用
        """
        return (self.enabled and self.access_key is not None and 
                self.secret_key is not None and self.bucket_name is not None)
    
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
            return True
        except Exception as e:
            logger.error(f"确保七牛云备份环境就绪失败: {str(e)}")
            return False
    
    def _ensure_bucket_exists(self) -> None:
        """
        确保存储桶存在
        """
        try:
            buckets, _ = self.bucket_manager.list_bucket(self.region)
            buckets = buckets or []
            bucket_ids = [bucket['id'] for bucket in buckets]
            if not bucket_ids or self.bucket_name not in bucket_ids:
                self._create_bucket()
            else:
                logger.info(f"====> 七牛云 Bucket 已存在: {self.bucket_name}")
        except Exception as e:
            logger.error(f"====> 七牛云检查或创建 bucket: {self.bucket_name} 时出错: {str(e)}")
            raise
    
    def _create_bucket(self) -> None:
        """
        创建存储桶
        """
        try:
            ret, info = self.bucket_manager.mkbucketv3(self.bucket_name, self.region)
            if info.status_code == 200:
                logger.info(f"====> 七牛云成功创建 Bucket: {self.bucket_name}")
                self._change_bucket_permission(self.PRIVATE)
            else:
                logger.error(f"====> 七牛云创建 Bucket 失败: {self.bucket_name}, 错误信息: {info}")
                raise Exception(f"创建 bucket 失败: {info}")
        except Exception as e:
            logger.error(f"====> 七牛云创建 bucket: {self.bucket_name} 时出错: {str(e)}")
            raise
    
    def _change_bucket_permission(self, private: str) -> None:
        """
        修改存储桶权限
        
        Args:
            private: 权限类型，'1'表示私有，'0'表示公有
        """
        try:
            if private not in (self.PRIVATE, self.PUBLIC):
                raise ValueError("无效的权限参数")
            private_desc = "私有" if private == self.PRIVATE else "公有"
            ret, info = self.bucket_manager.change_bucket_permission(self.bucket_name, private)
            if info.status_code == 200:
                logger.info(f"====> 七牛云设置 Bucket: {self.bucket_name} {private_desc} 属性成功")
            else:
                logger.error(f"====> 七牛云设置 Bucket: {self.bucket_name} {private_desc} 属性失败, 错误信息: {info}")
        except Exception as e:
            logger.error(f"====> 七牛云设置 bucket: {self.bucket_name} 权限时出错: {str(e)}")
            raise
    
    def _set_lifecycle_rule(self) -> None:
        """
        设置生命周期规则
        """
        try:
            logger.info(f"七牛云不支持直接设置生命周期规则，请在七牛云控制台手动设置")
        except Exception as e:
            logger.error(f"====> 七牛云设置生命周期规则失败: {str(e)}")
    
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
            logger.warning("七牛云备份未启用")
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
            
            # 生成上传凭证
            token = self.auth.upload_token(self.bucket_name, key)
            
            # 上传文件
            ret, info = put_file(token, key, source_file)
            
            if ret and ret.get('key') == key:
                logger.info(f"====> 七牛云备份成功: {source_file} -> {self.bucket_name}/{key}")
                return f"{self.bucket_name}/{key}"
            else:
                logger.error(f"====> 七牛云备份失败: {source_file}, 错误: {info}")
                return None
        except Exception as e:
            logger.error(f"====> 七牛云备份异常: {source_file}, 错误: {str(e)}")
            return None

# 创建实例并注册
qiniu_backup = QiniuBackup()
