import os
import time
import json
import shutil
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
class AgentInstaller(InstallerBase):
    """
    哪吒Agent安装器
    """

    def __init__(self):
        self.config = None
        self.version = "v0"  # 默认版本
        self.install_dir = None
        self.script_dir = None
        self.agent_script = None
        self.user_name = None

    def initialize(self, config: ConfigBase, version: str = "v0", user_name: Optional[str] = None) -> None:
        """
        初始化安装器

        Args:
            config: 配置实例
            version: 哪吒Agent版本，"v0" 或 "v1"
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
        from utils.system import get_agent_dir
        self.install_dir = get_agent_dir(self.user_name)

        # 获取脚本目录
        self.script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 设置安装脚本
        if self.version == "v1":
            self.agent_script = os.path.join(self.script_dir, 'download_nezha_v1.sh')
        else:
            self.agent_script = os.path.join(self.script_dir, 'download_nezha.sh')

    def check_environment(self) -> Tuple[bool, str]:
        """
        检查安装环境

        Returns:
            Tuple[bool, str]: 环境是否满足要求和消息
        """
        # 检查安装脚本是否存在
        if not check_file_exists(self.agent_script):
            return False, f"安装脚本不存在: {self.agent_script}"

        # 检查安装目录
        if not ensure_dir_exists(self.install_dir):
            return False, f"创建安装目录失败: {self.install_dir}"

        # 检查执行权限
        if not os.access(self.agent_script, os.X_OK):
            try:
                os.chmod(self.agent_script, 0o755)
            except Exception as e:
                return False, f"设置安装脚本执行权限失败: {str(e)}"

        return True, "环境检查通过"

    def download(self) -> Tuple[bool, str]:
        """
        下载安装包

        Returns:
            Tuple[bool, str]: 下载是否成功和消息
        """
        logger.info(f"开始下载哪吒Agent {self.version} 安装包")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message=f"开始下载哪吒Agent {self.version} 安装包")

        # 清理旧文件
        if os.path.exists(self.install_dir):
            try:
                # 备份配置文件
                agent_script = os.path.join(self.install_dir, 'nezha-agent.sh')
                if os.path.exists(agent_script):
                    backup_file = f"{agent_script}.bak"
                    shutil.copy2(agent_script, backup_file)
                    logger.info(f"已备份配置文件: {backup_file}")
            except Exception as e:
                logger.error(f"备份配置文件失败: {str(e)}")

        # 执行下载脚本
        success = run_shell_script(self.agent_script, "agent", self.install_dir)

        if success:
            return True, "下载哪吒Agent安装包成功"
        else:
            return False, "下载哪吒Agent安装包失败"

    def install(self) -> Tuple[bool, str]:
        """
        执行安装

        Returns:
            Tuple[bool, str]: 安装是否成功和消息
        """
        logger.info("开始安装哪吒Agent")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始安装哪吒Agent")

        # 检查安装文件
        exec_file = os.path.join(self.install_dir, 'nezha-agent')
        if not check_file_exists(exec_file):
            return False, f"安装失败，找不到执行文件: {exec_file}"

        # 设置执行权限
        try:
            os.chmod(exec_file, 0o755)

            # 设置脚本执行权限
            agent_script = os.path.join(self.install_dir, 'nezha-agent.sh')
            if check_file_exists(agent_script):
                os.chmod(agent_script, 0o755)
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
            "nezha-agent",
            "sh nezha-agent.sh",
            "foreground"
        )

        if not success:
            return False, "配置进程监控失败"

        return True, "安装哪吒Agent成功"

    def configure(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        配置安装

        Args:
            config: 配置参数，必须包含 'server' 和 'key'

        Returns:
            Tuple[bool, str]: 配置是否成功和消息
        """
        logger.info("开始配置哪吒Agent")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始配置哪吒Agent")

        # 检查必要参数
        if 'server' not in config or 'key' not in config:
            return False, "缺少必要的配置参数 'server' 或 'key'"

        # 配置脚本路径
        agent_script = os.path.join(self.install_dir, 'nezha-agent.sh')

        # 创建配置脚本
        server = config['server']
        key = config['key']

        # 创建脚本内容
        script_content = f"""#!/bin/bash
NZ_SERVER="{server}"
NZ_KEY="{key}"

# restart/stop/start
ACTION=$1
EXEC_DIR=$(dirname $(readlink -f "$0"))

# 请先正常退出旧的Agent进程
if [[ -n $NZ_AGENT_PID && -e /proc/$NZ_AGENT_PID ]]; then
    kill -9 $NZ_AGENT_PID || true
    unset NZ_AGENT_PID
fi

# 停止服务
if [[ $ACTION == stop || $ACTION == restart ]]; then
    if [[ -e $EXEC_DIR/nezha-agent ]]; then
        pkill -f $EXEC_DIR/nezha-agent || true
    fi
fi

# 启动服务
if [[ $ACTION == start || $ACTION == restart || -z $ACTION ]]; then
    if [[ -e $EXEC_DIR/nezha-agent ]]; then
        ($EXEC_DIR/nezha-agent -s $NZ_SERVER -p $NZ_KEY >/dev/null 2>&1 &)
    fi
fi
"""

        try:
            with open(agent_script, 'w') as f:
                f.write(script_content)

            # 设置执行权限
            os.chmod(agent_script, 0o755)
        except Exception as e:
            return False, f"创建Agent配置脚本失败: {str(e)}"

        return True, "配置哪吒Agent成功"

    def start(self) -> Tuple[bool, str]:
        """
        启动服务

        Returns:
            Tuple[bool, str]: 启动是否成功和消息
        """
        logger.info("开始启动哪吒Agent")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始启动哪吒Agent")

        # 使用进程监控脚本启动
        heart_beat_entry_file = os.path.join(self.script_dir, 'heart_beat_entry.sh')

        # 构建参数
        from utils.system import make_heart_beat_extra_info
        param = make_heart_beat_extra_info(None, os.uname()[1], self.user_name)

        # 执行启动脚本
        success = run_shell_script(heart_beat_entry_file, param)

        if not success:
            return False, "启动哪吒Agent失败"

        # 等待一段时间，确保服务启动
        time.sleep(2)

        # 检查服务状态
        is_running, status_msg = self.check_status()
        if is_running:
            return True, "启动哪吒Agent成功"
        else:
            return False, f"启动哪吒Agent后检查状态失败: {status_msg}"

    def stop(self) -> Tuple[bool, str]:
        """
        停止服务

        Returns:
            Tuple[bool, str]: 停止是否成功和消息
        """
        logger.info("开始停止哪吒Agent")
        event_bus.publish(EventTypes.SYSTEM_EVENT, message="开始停止哪吒Agent")

        # 查找进程
        code, stdout, _ = run_shell_command("pgrep -f nezha-agent")

        if code != 0:
            return True, "哪吒Agent未运行"

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
            return False, "停止哪吒Agent失败，进程仍在运行"

        return True, "停止哪吒Agent成功"

    def check_status(self) -> Tuple[bool, str]:
        """
        检查服务状态

        Returns:
            Tuple[bool, str]: 服务是否运行和消息
        """
        # 检查进程
        code, stdout, _ = run_shell_command("pgrep -f nezha-agent")

        if code == 0 and stdout.strip():
            return True, "哪吒Agent正在运行"

        return False, "哪吒Agent未运行"

    def get_version(self) -> Optional[str]:
        """
        获取安装的版本

        Returns:
            Optional[str]: 版本号，如果获取失败则返回None
        """
        exec_file = os.path.join(self.install_dir, 'nezha-agent')

        if not check_file_exists(exec_file):
            return None

        # 获取版本信息
        code, stdout, _ = run_shell_command(f"{exec_file} -v")

        if code == 0 and stdout.strip():
            return stdout.strip()

        return None

# 创建单例实例
agent_installer = AgentInstaller()
