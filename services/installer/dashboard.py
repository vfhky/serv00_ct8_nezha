import os
import time
import json
import shutil
import yaml
from typing import Dict, Any, Optional, List, Tuple

from services.installer.base import InstallerBase
from config.base import ConfigBase
from utils.logger import get_logger
from utils.system import run_shell_script, run_shell_command
from utils.file import ensure_dir_exists, check_file_exists, read_file, write_to_file
from utils.events import get_event_bus, EventTypes
from utils.decorators import singleton

logger = get_logger()
event_bus = get_event_bus()

@singleton
class DashboardInstaller(InstallerBase):
    """
    哪吒面板安装器
    """

    def __init__(self):
        self.config = None
        self.version = "v0"  # 默认版本
        self.install_dir = None
        self.script_dir = None
        self.dashboard_script = None
        self.user_name = None

    def initialize(self, config: ConfigBase, version: str = "v0", user_name: Optional[str] = None) -> None:
        """
        初始化安装器

        Args:
            config: 配置实例
            version: 哪吒面板版本，"v0" 或 "v1"
            user_name: 用户名，如果不指定则使用当前用户
        """
        self.config = config
        self.version = version

        # 获取用户名
        if user_name:
            self.user_name = user_name
        else:
            import getpass
            self.user_name = getpass.getuser()

        # 设置安装目录
        from utils.system import get_dashboard_dir
        self.install_dir = get_dashboard_dir(self.user_name)

        # 获取脚本目录
        self.script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 设置安装脚本
        if self.version == "v1":
            self.dashboard_script = os.path.join(self.script_dir, 'download_nezha_v1.sh')
        else:
            self.dashboard_script = os.path.join(self.script_dir, 'download_nezha.sh')

    def check_environment(self) -> Tuple[bool, str]:
        """
        检查安装环境

        Returns:
            Tuple[bool, str]: 环境是否满足要求和消息
        """
        # 检查安装脚本是否存在
        if not check_file_exists(self.dashboard_script):
            return False, f"安装脚本不存在: {self.dashboard_script}"

        # 检查安装目录
        if not ensure_dir_exists(self.install_dir):
            return False, f"创建安装目录失败: {self.install_dir}"

        # 检查执行权限
        if not os.access(self.dashboard_script, os.X_OK):
            try:
                os.chmod(self.dashboard_script, 0o755)
            except Exception as e:
                return False, f"设置安装脚本执行权限失败: {str(e)}"

        # 检查系统依赖
        code, _, stderr = run_shell_command("which unzip")
        if code != 0:
            return False, "未安装unzip，请先安装"

        return True, "环境检查通过"

    def download(self) -> Tuple[bool, str]:
        """
        下载安装包

        Returns:
            Tuple[bool, str]: 下载是否成功和消息
        """
        logger.info(f"开始下载哪吒面板 {self.version} 安装包")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message=f"开始下载哪吒面板 {self.version} 安装包")

        # 清理旧文件
        if os.path.exists(self.install_dir):
            try:
                # 备份配置文件
                config_dir = os.path.join(self.install_dir, 'data')
                config_file = os.path.join(config_dir, 'config.yaml')
                if os.path.exists(config_file):
                    backup_file = f"{config_file}.bak"
                    shutil.copy2(config_file, backup_file)
                    logger.info(f"已备份配置文件: {backup_file}")
            except Exception as e:
                logger.error(f"备份配置文件失败: {str(e)}")

        # 执行下载脚本
        success = run_shell_script(self.dashboard_script, "dashboard", self.install_dir)

        if success:
            return True, "下载哪吒面板安装包成功"
        else:
            return False, "下载哪吒面板安装包失败"

    def install(self) -> Tuple[bool, str]:
        """
        执行安装

        Returns:
            Tuple[bool, str]: 安装是否成功和消息
        """
        logger.info("开始安装哪吒面板")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始安装哪吒面板")

        # 检查安装文件
        exec_file = os.path.join(self.install_dir, 'nezha-dashboard')
        if not check_file_exists(exec_file):
            return False, f"安装失败，找不到执行文件: {exec_file}"

        # 确保数据目录存在
        data_dir = os.path.join(self.install_dir, 'data')
        if not ensure_dir_exists(data_dir):
            return False, f"创建数据目录失败: {data_dir}"

        # 设置执行权限
        try:
            os.chmod(exec_file, 0o755)
        except Exception as e:
            return False, f"设置执行文件权限失败: {str(e)}"

        # 配置进程监控
        utils_sh_file = os.path.join(self.script_dir, 'utils.sh')
        config_dir = os.path.join(self.script_dir, 'config')
        monitor_config_file = os.path.join(config_dir, 'monitor.conf')

        # 使用shell脚本配置监控
        success = run_shell_script(
            utils_sh_file,
            'monitor',
            monitor_config_file,
            self.install_dir,
            "nezha-dashboard",
            "./nezha-dashboard",
            "background"
        )

        if not success:
            return False, "配置进程监控失败"

        return True, "安装哪吒面板成功"

    def configure(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        配置安装

        Args:
            config: 配置参数

        Returns:
            Tuple[bool, str]: 配置是否成功和消息
        """
        logger.info("开始配置哪吒面板")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始配置哪吒面板")

        # 配置文件路径
        config_dir = os.path.join(self.install_dir, 'data')
        config_file = os.path.join(config_dir, 'config.yaml')

        # 如果没有配置文件，创建默认配置
        if not check_file_exists(config_file):
            default_config = {
                'Debug': False,
                'HTTPPort': config.get('HTTPPort', 8008),
                'Language': 'zh-CN',
                'GRPCPort': config.get('GRPCPort', 5555),
                'GRPCHost': config.get('GRPCHost', '0.0.0.0'),
                'ProxyGRPCPort': config.get('ProxyGRPCPort', 5555),
                'TLS': config.get('TLS', False),
                'EnableIPChangeAlert': config.get('EnableIPChangeAlert', True),
                'Site': {
                    'Brand': config.get('SiteBrand', 'Nezha Monitoring'),
                    'Theme': config.get('SiteTheme', 'default'),
                    'CustomCode': config.get('SiteCustomCode', ''),
                    'ViewPassword': config.get('SiteViewPassword', '')
                },
                'OAuth2': {
                    'Type': config.get('OAuth2Type', 'github'),
                    'Admin': config.get('OAuth2Admin', ''),
                    'ClientID': config.get('OAuth2ClientID', ''),
                    'ClientSecret': config.get('OAuth2ClientSecret', '')
                },
                'Notification': {
                    'WebHook': {
                        'Enabled': config.get('NotificationWebHookEnabled', True)
                    }
                }
            }

            try:
                with open(config_file, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
            except Exception as e:
                return False, f"创建默认配置文件失败: {str(e)}"

        # 如果有配置参数，更新现有配置
        elif config:
            try:
                with open(config_file, 'r') as f:
                    current_config = yaml.safe_load(f)

                # 更新配置
                if 'HTTPPort' in config:
                    current_config['HTTPPort'] = config['HTTPPort']
                if 'GRPCPort' in config:
                    current_config['GRPCPort'] = config['GRPCPort']
                if 'GRPCHost' in config:
                    current_config['GRPCHost'] = config['GRPCHost']

                # 更新站点配置
                if 'Site' not in current_config:
                    current_config['Site'] = {}
                if 'SiteBrand' in config:
                    current_config['Site']['Brand'] = config['SiteBrand']
                if 'SiteTheme' in config:
                    current_config['Site']['Theme'] = config['SiteTheme']
                if 'SiteViewPassword' in config:
                    current_config['Site']['ViewPassword'] = config['SiteViewPassword']

                # 更新OAuth2配置
                if 'OAuth2' not in current_config:
                    current_config['OAuth2'] = {}
                if 'OAuth2Type' in config:
                    current_config['OAuth2']['Type'] = config['OAuth2Type']
                if 'OAuth2Admin' in config:
                    current_config['OAuth2']['Admin'] = config['OAuth2Admin']
                if 'OAuth2ClientID' in config:
                    current_config['OAuth2']['ClientID'] = config['OAuth2ClientID']
                if 'OAuth2ClientSecret' in config:
                    current_config['OAuth2']['ClientSecret'] = config['OAuth2ClientSecret']

                # 写入更新后的配置
                with open(config_file, 'w') as f:
                    yaml.dump(current_config, f, default_flow_style=False)

            except Exception as e:
                return False, f"更新配置文件失败: {str(e)}"

        return True, "配置哪吒面板成功"

    def start(self) -> Tuple[bool, str]:
        """
        启动服务

        Returns:
            Tuple[bool, str]: 启动是否成功和消息
        """
        logger.info("开始启动哪吒面板")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始启动哪吒面板")

        # 使用进程监控脚本启动
        heart_beat_entry_file = os.path.join(self.script_dir, 'heart_beat_entry.sh')

        # 构建参数
        from utils.system import make_heart_beat_extra_info
        param = make_heart_beat_extra_info(None, os.uname()[1], self.user_name)

        # 执行启动脚本
        success = run_shell_script(heart_beat_entry_file, param)

        if not success:
            return False, "启动哪吒面板失败"

        # 等待一段时间，确保服务启动
        time.sleep(2)

        # 检查服务状态
        is_running, status_msg = self.check_status()
        if is_running:
            # 显示Agent Key
            utils_sh_file = os.path.join(self.script_dir, 'utils.sh')
            from utils.system import get_dashboard_config_file
            config_file = get_dashboard_config_file(self.user_name)

            run_shell_script(utils_sh_file, "show_agent_key", config_file)

            return True, "启动哪吒面板成功"
        else:
            return False, f"启动哪吒面板后检查状态失败: {status_msg}"

    def stop(self) -> Tuple[bool, str]:
        """
        停止服务

        Returns:
            Tuple[bool, str]: 停止是否成功和消息
        """
        logger.info("开始停止哪吒面板")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始停止哪吒面板")

        # 查找进程
        code, stdout, _ = run_shell_command("pgrep -f nezha-dashboard")

        if code != 0:
            return True, "哪吒面板未运行"

        # 停止进程
        for pid in stdout.strip().split('\n'):
            if pid:
                run_shell_command(f"kill -15 {pid}")
                time.sleep(1)

                # 检查是否还在运行
                check_code, _, _ = run_shell_command(f"kill -0 {pid} 2>/dev/null")
                if check_code == 0:
                    # 强制终止
                    run_shell_command(f"kill -9 {pid}")

        # 验证是否已停止
        time.sleep(1)
        is_running, _ = self.check_status()
        if is_running:
            return False, "停止哪吒面板失败，进程仍在运行"

        return True, "停止哪吒面板成功"

    def check_status(self) -> Tuple[bool, str]:
        """
        检查服务状态

        Returns:
            Tuple[bool, str]: 服务是否运行和消息
        """
        # 检查进程
        code, stdout, _ = run_shell_command("pgrep -f nezha-dashboard")

        if code == 0 and stdout.strip():
            # 检查端口
            config_dir = os.path.join(self.install_dir, 'data')
            config_file = os.path.join(config_dir, 'config.yaml')

            try:
                if check_file_exists(config_file):
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)

                    port = config.get('HTTPPort', 8008)

                    # 检查端口是否监听
                    port_code, port_stdout, _ = run_shell_command(f"netstat -tuln | grep :{port}")

                    if port_code == 0 and port_stdout.strip():
                        return True, f"哪吒面板正在运行，HTTP端口: {port}"
                    else:
                        return True, "哪吒面板进程正在运行，但HTTP端口未监听"

                return True, "哪吒面板进程正在运行"

            except Exception as e:
                return True, f"哪吒面板进程正在运行，但读取配置失败: {str(e)}"

        return False, "哪吒面板未运行"

    def get_version(self) -> Optional[str]:
        """
        获取安装的版本

        Returns:
            Optional[str]: 版本号，如果获取失败则返回None
        """
        exec_file = os.path.join(self.install_dir, 'nezha-dashboard')

        if not check_file_exists(exec_file):
            return None

        # 获取版本信息
        code, stdout, _ = run_shell_command(f"{exec_file} version")

        if code == 0 and stdout.strip():
            return stdout.strip()

        return None

    def get_agent_key(self) -> Optional[str]:
        """
        获取Agent Key

        Returns:
            Optional[str]: Agent Key，如果获取失败则返回None
        """
        config_dir = os.path.join(self.install_dir, 'data')
        config_file = os.path.join(config_dir, 'config.yaml')

        if not check_file_exists(config_file):
            return None

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            return config.get('PasswordSalt', None)
        except Exception:
            return None

# 创建单例实例
dashboard_installer = DashboardInstaller()
