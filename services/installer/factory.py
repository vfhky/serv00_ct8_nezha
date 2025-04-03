from typing import Dict, Optional, Type, Any
from core.installer.base import InstallerBase
from core.installer.dashboard import DashboardInstaller, dashboard_installer
from core.installer.agent import AgentInstaller, agent_installer
from config.base import ConfigBase
from utils.logger import get_logger

logger = get_logger()

class InstallerFactory:
    """
    安装器工厂，负责创建和管理各种安装器
    """
    _installers: Dict[str, InstallerBase] = {}
    
    @staticmethod
    def register_installer(name: str, installer: InstallerBase) -> None:
        """
        注册安装器
        
        Args:
            name: 安装器名称
            installer: 安装器实例
        """
        InstallerFactory._installers[name] = installer
        logger.info(f"已注册安装器: {name}")
    
    @staticmethod
    def get_installer(name: str) -> Optional[InstallerBase]:
        """
        获取安装器
        
        Args:
            name: 安装器名称
            
        Returns:
            Optional[InstallerBase]: 安装器实例，如果不存在则返回None
        """
        return InstallerFactory._installers.get(name)
    
    @staticmethod
    def create_installers(config: ConfigBase) -> Dict[str, InstallerBase]:
        """
        创建所有安装器
        
        Args:
            config: 配置实例
            
        Returns:
            Dict[str, InstallerBase]: 安装器名称到安装器实例的映射
        """
        # 初始化安装器
        dashboard_installer.initialize(config)
        agent_installer.initialize(config)
        
        # 注册安装器
        InstallerFactory.register_installer('dashboard', dashboard_installer)
        InstallerFactory.register_installer('agent', agent_installer)
        
        return InstallerFactory._installers
    
    @staticmethod
    def create_dashboard_installer(config: ConfigBase, version: str = "v0") -> DashboardInstaller:
        """
        创建哪吒面板安装器
        
        Args:
            config: 配置实例
            version: 哪吒面板版本，"v0" 或 "v1"
            
        Returns:
            DashboardInstaller: 哪吒面板安装器实例
        """
        installer = dashboard_installer
        installer.initialize(config, version)
        InstallerFactory.register_installer('dashboard', installer)
        
        return installer
    
    @staticmethod
    def create_agent_installer(config: ConfigBase, version: str = "v0") -> AgentInstaller:
        """
        创建哪吒Agent安装器
        
        Args:
            config: 配置实例
            version: 哪吒Agent版本，"v0" 或 "v1"
            
        Returns:
            AgentInstaller: 哪吒Agent安装器实例
        """
        installer = agent_installer
        installer.initialize(config, version)
        InstallerFactory.register_installer('agent', installer)
        
        return installer
