import os
from datetime import datetime
from typing import Optional
from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError, CosClientError
from services.backup.base import BackupBase
from services.backup.factory import BackupFactory
from config.base import ConfigBase
from utils.logger import get_logger
from utils.decorators import singleton

logger = get_logger()

@singleton
class TencentCosBackup(BackupBase):
    """
    腾讯云COS备份实现
    """
    DATE_FORMAT = '%d'
    MONTH_FORMAT = '%Y%m'

    def __init__(self):
        self.enabled = False
        self.app_id = None
        self.secret_id = None
        self.secret_key = None
        self.region = None
        self.bucket_name = None
        self.dir_name = None
        self.ttl = 7
        self.client = None

    @classmethod
    def initialize(cls, config: ConfigBase) -> 'TencentCosBackup':
        """
        初始化备份实例

        Args:
            config: 配置实例

        Returns:
            TencentCosBackup: 备份实例
        """
        instance = cls()
        instance.enabled = config.get('ENABLE_QCLOUD_COS_BACKUP') == '1'
        instance.app_id = config.get('QCLOUD_COS_APP_ID')
        instance.secret_id = config.get('QCLOUD_COS_SECRET_ID')
        instance.secret_key = config.get('QCLOUD_COS_SECRET_KEY')
        instance.region = config.get('QCLOUD_COS_REGION')
        instance.bucket_name = config.get('QCLOUD_COS_BUCKET_NAME')
        instance.dir_name = config.get('QCLOUD_COS_DIR_NAME')

        try:
            instance.ttl = int(config.get('QCLOUD_COS_EXPIRE_DAYS', 7))
        except (ValueError, TypeError):
            instance.ttl = 7

        if instance.enabled:
            if not instance.secret_id or not instance.secret_key:
                logger.warning("腾讯云COS备份已启用，但未配置密钥")
                instance.enabled = False
            elif not instance.bucket_name:
                logger.warning("腾讯云COS备份已启用，但未配置存储桶名称")
                instance.enabled = False
            else:
                # 初始化腾讯云COS客户端
                cos_config = CosConfig(
                    Region=instance.region,
                    SecretId=instance.secret_id,
                    SecretKey=instance.secret_key
                )
                instance.client = CosS3Client(cos_config)

        # 注册到工厂
        BackupFactory.register_backup('tencent', instance)

        return instance

    def is_enabled(self) -> bool:
        """
        检查备份服务是否启用

        Returns:
            bool: 服务是否启用
        """
        return (self.enabled and self.secret_id is not None and
                self.secret_key is not None and self.bucket_name is not None and
                self.client is not None)

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
            self.set_bucket_lifecycle()
            return True
        except Exception as e:
            logger.error(f"确保腾讯云COS备份环境就绪失败: {str(e)}")
            return False

    def _ensure_bucket_exists(self) -> None:
        """
        确保存储桶存在
        """
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"腾讯云COS Bucket 已存在: {self.bucket_name}")
        except CosServiceError as e:
            if e.get_status_code() == 404:
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"腾讯云COS创建 Bucket 成功: {self.bucket_name}")
                except Exception as create_error:
                    logger.error(f"腾讯云COS创建 Bucket 失败: {self.bucket_name}, 错误: {str(create_error)}")
                    raise
            else:
                logger.error(f"腾讯云COS检查 Bucket 时出错: {self.bucket_name}, 错误: {str(e)}")
                raise

    def set_bucket_lifecycle(self) -> None:
        """
        设置存储桶生命周期规则
        """
        try:
            rule = {
                'ID': 'DeleteAfterDays',
                'Status': 'Enabled',
                'Filter': {'Prefix': self.dir_name},
                'Expiration': {'Days': self.ttl}
            }

            lifecycle_config = {
                'Rule': [rule]
            }

            response = self.client.put_bucket_lifecycle(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            logger.info(f"腾讯云COS成功设置存储桶 {self.bucket_name} 的生命周期规则")
        except (CosServiceError, CosClientError) as e:
            logger.error(f"腾讯云COS设置存储桶 {self.bucket_name} 的生命周期规则失败：{str(e)}")
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
            logger.warning("腾讯云COS备份未启用")
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
            with open(source_file, 'rb') as fp:
                response = self.client.put_object(
                    Bucket=self.bucket_name,
                    Body=fp,
                    Key=key,
                    EnableMD5=True,
                    StorageClass='STANDARD'
                )

            if 'ETag' in response:
                logger.info(f"====> 腾讯云COS备份成功: {source_file} -> {self.bucket_name}/{key}")
                return f"{self.bucket_name}/{key}"
            else:
                logger.error(f"====> 腾讯云COS备份失败: {source_file}, 响应: {response}")
                return None
        except Exception as e:
            logger.error(f"====> 腾讯云COS备份异常: {source_file}, 错误: {str(e)}")
            return None

# 创建实例并注册
tencent_backup = TencentCosBackup()
