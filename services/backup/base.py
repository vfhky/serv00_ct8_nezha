# services/backup/base.py
from abc import ABC, abstractmethod
from typing import Optional

class BackupBase(ABC):
    """
    备份服务基类，定义了备份的基本接口
    """
    
    @abstractmethod
    def backup(self, source_file: str, target_path: Optional[str] = None) -> Optional[str]:
        """
        备份文件
        
        Args:
            source_file: 源文件路径
            target_path: 目标路径，可选
            
        Returns:
            Optional[str]: 备份文件的路径或标识符，如果备份失败则返回None
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        检查备份服务是否启用
        
        Returns:
            bool: 服务是否启用
        """
        pass
    
    @abstractmethod
    def ensure_backup_environment(self) -> bool:
        """
        确保备份环境已准备就绪（如创建存储桶等）
        
        Returns:
            bool: 环境是否准备就绪
        """
        pass