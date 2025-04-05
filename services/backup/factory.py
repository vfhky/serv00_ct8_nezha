from typing import Dict, List, Optional, Type
from services.backup.base import BackupBase
from config.base import ConfigBase
from utils.logger import get_logger

logger = get_logger()

class BackupFactory:
    """
    备份服务工厂，负责创建和管理各种备份实现
    """
    _backups: Dict[str, BackupBase] = {}

    @staticmethod
    def register_backup(name: str, backup: BackupBase) -> None:
        """
        注册备份实现

        Args:
            name: 备份名称
            backup: 备份实例
        """
        BackupFactory._backups[name] = backup
        logger.info(f"已注册备份服务: {name}")

    @staticmethod
    def get_backup(name: str) -> Optional[BackupBase]:
        """
        获取备份实现

        Args:
            name: 备份名称

        Returns:
            Optional[BackupBase]: 备份实例，如果不存在则返回None
        """
        return BackupFactory._backups.get(name)

    @staticmethod
    def create_backups(config: ConfigBase) -> Dict[str, BackupBase]:
        """
        根据配置创建所有可用的备份实现

        Args:
            config: 配置实例

        Returns:
            Dict[str, BackupBase]: 备份名称到备份实例的映射
        """
        # 导入所有备份实现
        # 注意: 这些导入语句会触发各实现类的注册
        from services.backup.qiniu import qiniu_backup
        from services.backup.tencent import tencent_cos_backup
        from services.backup.aliyun import aliyun_oss_backup

        # 根据配置初始化所有备份实现
        qiniu_backup.initialize(config)
        tencent_cos_backup.initialize(config)
        aliyun_oss_backup.initialize(config)

        return BackupFactory._backups

    @staticmethod
    def get_enabled_backups() -> List[BackupBase]:
        """
        获取所有已启用的备份实现

        Returns:
            List[BackupBase]: 已启用的备份实例列表
        """
        return [backup for backup in BackupFactory._backups.values() if backup.is_enabled()]

    @staticmethod
    def backup_all(source_file: str, target_path: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        使用所有已启用的备份服务备份文件

        Args:
            source_file: 源文件路径
            target_path: 目标路径，可选

        Returns:
            Dict[str, Optional[str]]: 备份名称到备份结果的映射
        """
        backups = BackupFactory.get_enabled_backups()
        if not backups:
            logger.warning("没有启用的备份服务")
            return {}

        results = {}
        for backup in backups:
            try:
                result = backup.backup(source_file, target_path)
                results[backup.__class__.__name__] = result
            except Exception as e:
                logger.error(f"备份失败: {backup.__class__.__name__}, 错误: {str(e)}")
                results[backup.__class__.__name__] = None

        return results
