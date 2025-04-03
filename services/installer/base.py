from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple

class InstallerBase(ABC):
    """
    安装器基类，定义了安装过程的基本接口
    """
    
    @abstractmethod
    def check_environment(self) -> Tuple[bool, str]:
        """
        检查安装环境
        
        Returns:
            Tuple[bool, str]: 环境是否满足要求和消息
        """
        pass
    
    @abstractmethod
    def download(self) -> Tuple[bool, str]:
        """
        下载安装包
        
        Returns:
            Tuple[bool, str]: 下载是否成功和消息
        """
        pass
    
    @abstractmethod
    def install(self) -> Tuple[bool, str]:
        """
        执行安装
        
        Returns:
            Tuple[bool, str]: 安装是否成功和消息
        """
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        配置安装
        
        Args:
            config: 配置参数
            
        Returns:
            Tuple[bool, str]: 配置是否成功和消息
        """
        pass
    
    @abstractmethod
    def start(self) -> Tuple[bool, str]:
        """
        启动服务
        
        Returns:
            Tuple[bool, str]: 启动是否成功和消息
        """
        pass
    
    @abstractmethod
    def stop(self) -> Tuple[bool, str]:
        """
        停止服务
        
        Returns:
            Tuple[bool, str]: 停止是否成功和消息
        """
        pass
    
    @abstractmethod
    def check_status(self) -> Tuple[bool, str]:
        """
        检查服务状态
        
        Returns:
            Tuple[bool, str]: 服务是否运行和消息
        """
        pass
    
    @abstractmethod
    def get_version(self) -> Optional[str]:
        """
        获取安装的版本
        
        Returns:
            Optional[str]: 版本号，如果获取失败则返回None
        """
        pass
