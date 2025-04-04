import os
from typing import Dict, Any, Optional, List, Tuple

from core.installer.base import InstallerBase
from core.installer.factory import InstallerFactory
from core.installer.dashboard import DashboardInstaller
from core.installer.agent import AgentInstaller
from config.base import ConfigBase
from utils.logger import get_logger
from utils.events import get_event_bus, EventTypes
from utils.decorators import singleton

logger = get_logger()
event_bus = get_event_bus()

@singleton
class InstallationManager:
    """
    安装管理器，统一管理安装过程
    """

    def __init__(self):
        self.config = None
        self.dashboard_installer = None
        self.agent_installer = None

    def initialize(self, config: ConfigBase) -> None:
        """
        初始化安装管理器

        Args:
            config: 配置实例
        """
        self.config = config
        self.dashboard_installer = InstallerFactory.create_dashboard_installer(config)
        self.agent_installer = InstallerFactory.create_agent_installer(config)

        logger.info("安装管理器初始化完成")

    def install_dashboard(self, config_params: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        安装哪吒面板

        Args:
            config_params: 配置参数

        Returns:
            Tuple[bool, str]: 安装是否成功和消息
        """
        logger.info("开始安装哪吒面板")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始安装哪吒面板")

        # 检查环境
        success, message = self.dashboard_installer.check_environment()
        if not success:
            logger.error(f"检查环境失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"检查环境失败: {message}")
            return False, message

        # 下载安装包
        success, message = self.dashboard_installer.download()
        if not success:
            logger.error(f"下载安装包失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"下载安装包失败: {message}")
            return False, message

        # 执行安装
        success, message = self.dashboard_installer.install()
        if not success:
            logger.error(f"执行安装失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"执行安装失败: {message}")
            return False, message

        # 配置安装
        if config_params:
            success, message = self.dashboard_installer.configure(config_params)
            if not success:
                logger.error(f"配置安装失败: {message}")
                event_bus.publish(EventTypes.ERROR_EVENT, message=f"配置安装失败: {message}")
                return False, message

        # 启动服务
        success, message = self.dashboard_installer.start()
        if not success:
            logger.error(f"启动服务失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"启动服务失败: {message}")
            return False, message

        logger.info("安装哪吒面板成功")
        event_bus.publish(EventTypes.SUCCESS_EVENT, message="安装哪吒面板成功")

        return True, message

    def install_agent(self, server: str, key: str) -> Tuple[bool, str]:
        """
        安装哪吒Agent

        Args:
            server: 服务器地址，格式为 grpc.example.com:5555
            key: Agent Key

        Returns:
            Tuple[bool, str]: 安装是否成功和消息
        """
        logger.info("开始安装哪吒Agent")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始安装哪吒Agent")

        # 检查环境
        success, message = self.agent_installer.check_environment()
        if not success:
            logger.error(f"检查环境失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"检查环境失败: {message}")
            return False, message

        # 下载安装包
        success, message = self.agent_installer.download()
        if not success:
            logger.error(f"下载安装包失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"下载安装包失败: {message}")
            return False, message

        # 执行安装
        success, message = self.agent_installer.install()
        if not success:
            logger.error(f"执行安装失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"执行安装失败: {message}")
            return False, message

        # 配置安装
        config_params = {
            'server': server,
            'key': key
        }

        success, message = self.agent_installer.configure(config_params)
        if not success:
            logger.error(f"配置安装失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"配置安装失败: {message}")
            return False, message

        # 启动服务
        success, message = self.agent_installer.start()
        if not success:
            logger.error(f"启动服务失败: {message}")
            event_bus.publish(EventTypes.ERROR_EVENT, message=f"启动服务失败: {message}")
            return False, message

        logger.info("安装哪吒Agent成功")
        event_bus.publish(EventTypes.SUCCESS_EVENT, message="安装哪吒Agent成功")

        return True, message

    def get_status(self) -> Dict[str, Any]:
        """
        获取安装状态

        Returns:
            Dict[str, Any]: 安装状态信息
        """
        result = {
            'dashboard': {
                'installed': False,
                'running': False,
                'version': None,
                'message': "",
                'agent_key': None
            },
            'agent': {
                'installed': False,
                'running': False,
                'version': None,
                'message': ""
            }
        }

        # 检查哪吒面板
        version = self.dashboard_installer.get_version()
        if version:
            result['dashboard']['installed'] = True
            result['dashboard']['version'] = version

            running, message = self.dashboard_installer.check_status()
            result['dashboard']['running'] = running
            result['dashboard']['message'] = message

            # 获取Agent Key
            agent_key = self.dashboard_installer.get_agent_key()
            if agent_key:
                result['dashboard']['agent_key'] = agent_key

        # 检查哪吒Agent
        version = self.agent_installer.get_version()
        if version:
            result['agent']['installed'] = True
            result['agent']['version'] = version

            running, message = self.agent_installer.check_status()
            result['agent']['running'] = running
            result['agent']['message'] = message

        return result

    def uninstall_dashboard(self) -> Tuple[bool, str]:
        """
        卸载哪吒面板

        Returns:
            Tuple[bool, str]: 卸载是否成功和消息
        """
        logger.info("开始卸载哪吒面板")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始卸载哪吒面板")

        # 停止服务
        success, message = self.dashboard_installer.stop()
        if not success:
            logger.warning(f"停止哪吒面板失败: {message}")

        # 删除安装目录
        import shutil
        try:
            from utils.system import get_dashboard_dir
            import getpass
            install_dir = get_dashboard_dir(getpass.getuser())

            if os.path.exists(install_dir):
                shutil.rmtree(install_dir)
                message = "卸载哪吒面板成功"
                success = True
            else:
                message = "哪吒面板未安装"
                success = True
        except Exception as e:
            message = f"删除哪吒面板安装目录失败: {str(e)}"
            logger.error(message)
            event_bus.publish(EventTypes.ERROR_EVENT, message=message)
            success = False

        if success:
            logger.info("卸载哪吒面板成功")
            event_bus.publish(EventTypes.SUCCESS_EVENT, message="卸载哪吒面板成功")

        return success, message

    def uninstall_agent(self) -> Tuple[bool, str]:
        """
        卸载哪吒Agent

        Returns:
            Tuple[bool, str]: 卸载是否成功和消息
        """
        logger.info("开始卸载哪吒Agent")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始卸载哪吒Agent")

        # 停止服务
        success, message = self.agent_installer.stop()
        if not success:
            logger.warning(f"停止哪吒Agent失败: {message}")

        # 删除安装目录
        import shutil
        try:
            from utils.system import get_agent_dir
            import getpass
            install_dir = get_agent_dir(getpass.getuser())

            if os.path.exists(install_dir):
                shutil.rmtree(install_dir)
                message = "卸载哪吒Agent成功"
                success = True
            else:
                message = "哪吒Agent未安装"
                success = True
        except Exception as e:
            message = f"删除哪吒Agent安装目录失败: {str(e)}"
            logger.error(message)
            event_bus.publish(EventTypes.ERROR_EVENT, message=message)
            success = False

        if success:
            logger.info("卸载哪吒Agent成功")
            event_bus.publish(EventTypes.SUCCESS_EVENT, message="卸载哪吒Agent成功")

        return success, message

# 创建单例实例
installation_manager = InstallationManager()
