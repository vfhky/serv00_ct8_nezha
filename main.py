#!/usr/bin/env python3
import os
import sys
import signal
import time
from typing import List, Dict, Optional
import asyncio
import traceback
import atexit
import glob

# 确保 src 目录在系统路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.config.host_config_entry import HostConfigEntry
from src.config.sys_config_entry import SysConfigEntry
from src.utils.async_utils import AsyncExecutor, shutdown_thread_pool
import src.utils.utils as utils
from src.utils.logger_wrapper import LoggerWrapper

# 初始化日志
logger = LoggerWrapper()

# 全局变量
shutdown_event = asyncio.Event()

# 注册清理函数
@atexit.register
def cleanup():
    logger.info("执行退出清理操作...")
    shutdown_thread_pool()
    logger.info("清理操作完成")

# 信号处理
def handle_shutdown_signal(signum, frame):
    logger.info(f"\n收到信号 {signum}，正在优雅退出...")
    shutdown_event.set()

async def transfer_ssh_file_to_host(entry: Dict, host_name: str, user_name: str, local_dir: str, host_id: int) -> None:
    client = entry.get('client')
    if not client:
        logger.info(f"==> [{host_id}]号主机未连接成功 [{entry['username']}@{entry['hostname']}:{entry['port']}]")
        return

    if entry['hostname'] == host_name and entry['username'] == user_name:
        logger.info(f"==> [{host_id}]号主机为当前主机，不需要处理")
        return

    logger.info(f"==> 开始拷贝到[{host_id}]号主机 [{entry['username']}@{entry['hostname']}:{entry['port']}]...")
    try:
        remote_dir = utils.get_ssh_dir(entry['username'])
        await AsyncExecutor.run_in_thread(client.transfer_files, local_dir, remote_dir)
        logger.info(f"==> [{host_id}]号主机文件拷贝成功")
    except Exception as e:
        error_msg = f"拷贝文件到[{host_id}]号主机失败: {str(e)}"
        logger.error(error_msg)

async def transfer_ssh_dir_to_all_hosts(config_entries: List[Dict], host_name: str, user_name: str, local_dir: str) -> None:
    if not config_entries:
        logger.info("警告: 没有配置任何主机，跳过SSH目录传输")
        return

    tasks = []
    for host_id, entry in enumerate(config_entries, 1):
        task = transfer_ssh_file_to_host(entry, host_name, user_name, local_dir, host_id)
        tasks.append(task)

    await AsyncExecutor.gather_with_concurrency(3, *tasks, ignore_exceptions=True)

async def gen_host_heart_beat_config(utils_sh_file: str, heart_beat_config_file: str, entry: Dict,
                                     host_name: str, user_name: str, host_id: int) -> None:
    if host_name == entry["hostname"] and user_name == entry["username"]:
        logger.info(f"====> [{host_id}]号主机[{user_name}@{host_name}]是当前主机，跳过不处理")
        return

    logger.info(f"====> 开始把[{host_id}]号主机[{user_name}@{host_name}]写入到心跳配置文件中{heart_beat_config_file}")
    try:
        result = await AsyncExecutor.run_in_thread(
            utils.run_shell_script_with_os,
            utils_sh_file, 'heart', heart_beat_config_file, entry["hostname"],
            str(entry["port"]), entry["username"]
        )
        if not result:
            error_msg = f"警告: 写入[{host_id}]号主机信息失败"
            logger.warning(error_msg)
    except Exception as e:
        error_msg = f"错误: 写入[{host_id}]号主机信息时发生异常: {str(e)}"
        logger.error(error_msg)

async def gen_all_hosts_heart_beat_config(utils_sh_file: str, heart_beat_config_file: str, config_entries: List[Dict],
                                         host_name: str, user_name: str) -> None:
    if not config_entries:
        logger.info("警告: 没有配置任何主机，跳过心跳配置生成")
        return

    logger.info(f"==> 开始把所有主机信息写入到心跳配置文件中{heart_beat_config_file}")

    tasks = []
    for host_id, entry in enumerate(config_entries, 1):
        task = gen_host_heart_beat_config(
            utils_sh_file, heart_beat_config_file, entry,
            host_name, user_name, host_id
        )
        tasks.append(task)

    await AsyncExecutor.gather_with_concurrency(5, *tasks, ignore_exceptions=True)

def gen_ed25519(utils_sh_file: str, ssh_dir: str) -> bool:
    # 确保目录存在
    if not os.path.exists(ssh_dir):
        try:
            os.makedirs(ssh_dir, exist_ok=True)
            os.chmod(ssh_dir, 0o700)
        except Exception as e:
            logger.error(f"创建SSH目录失败: {str(e)}")
            return False

    logger.info(f"===> 开始生成ed25519密钥对，密钥保存在{ssh_dir}目录...")
    return utils.run_shell_script_with_os(utils_sh_file, "keygen", ssh_dir)

@utils.time_count
async def main_async():
    try:
        host_name, user_name = utils.get_hostname_and_username()
        logger.info(f"===> 当前主机: {host_name}, 用户: {user_name}")

        # 定义环境
        ssh_dir = utils.get_ssh_dir(user_name)
        private_key_file = utils.get_ssh_ed25519_pri(user_name)

        # 应用安装目录
        dashboard_dir = utils.get_dashboard_dir(user_name)
        agent_dir = utils.get_agent_dir(user_name)

        # 当前脚本所在的目录
        serv00_ct8_dir = os.path.dirname(os.path.abspath(__file__))
        scripts_dir = os.path.join(serv00_ct8_dir, 'scripts')

        # 确保scripts目录存在
        if not os.path.exists(scripts_dir):
            logger.error(f"脚本目录不存在: {scripts_dir}")
            logger.info("正在创建scripts目录...")
            try:
                os.makedirs(scripts_dir, exist_ok=True)
                logger.info(f"成功创建scripts目录: {scripts_dir}")
            except Exception as e:
                logger.error(f"创建scripts目录失败: {str(e)}")
                return

        # 检查utils.sh等脚本是否存在
        utils_sh_file = os.path.join(scripts_dir, 'utils.sh')
        if not os.path.exists(utils_sh_file):
            logger.error(f"工具脚本不存在: {utils_sh_file}")
            logger.info("请确保项目已正确克隆，并且scripts目录包含所有必要的shell脚本")
            return

        # 设置所有shell脚本可执行权限
        shell_scripts = glob.glob(os.path.join(scripts_dir, '*.sh'))
        if not shell_scripts:
            logger.error(f"在{scripts_dir}中未找到任何shell脚本")
            return

        for script in shell_scripts:
            if not utils.ensure_file_permissions(script, 0o755):
                logger.warning(f"无法设置脚本权限: {script}")
            else:
                logger.info(f"已设置脚本权限: {script}")

        # 检查utils.sh脚本是否存在和权限
        if not os.path.exists(utils_sh_file):
            logger.error(f"工具脚本不存在: {utils_sh_file}")
            return

        # 确保脚本有执行权限
        if not utils.ensure_file_permissions(utils_sh_file, 0o755):
            logger.warning(f"无法设置脚本权限: {utils_sh_file}")

        # 生成配置文件
        logger.info(f"===> 从[config]目录生成配置文件...")
        config_dir = utils.get_serv00_config_dir(serv00_ct8_dir)

        # 确保配置目录存在
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
                os.chmod(config_dir, 0o755)
                logger.info(f"创建配置目录: {config_dir}")
            except Exception as e:
                logger.error(f"错误: 无法创建配置目录: {str(e)}")
                return

        if not utils.run_shell_script_with_os(utils_sh_file, 'rename_config', config_dir):
            logger.error("===> 从[config]目录生成配置文件失败，请检查serv00是否开启允许应用....")
            return

        logger.info(f"===> 从[config]目录生成配置文件成功....")

        # 定义配置文件路径
        sys_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'sys.conf')
        host_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'host.conf')
        monitor_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'monitor.conf')
        heart_beat_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'heartbeat.conf')

        # 检查配置文件
        missing_files = []
        for file_path, file_desc in [
            (sys_config_file, "系统配置"),
            (host_config_file, "主机配置"),
            (monitor_config_file, "监控配置"),
            (heart_beat_config_file, "心跳配置")
        ]:
            if not os.path.exists(file_path):
                missing_files.append(f"{file_desc}文件({file_path})")

        if missing_files:
            logger.warning(f"缺少配置文件: {', '.join(missing_files)}")

        # 加载系统配置
        sys_config = None
        try:
            sys_config = SysConfigEntry(sys_config_file)
            logger.info("系统配置加载成功")
        except Exception as e:
            logger.warning(f"加载系统配置失败: {str(e)}")

        # 初始化
        logger.info("===> 正在初始化环境...")
        try:
            if not utils.run_shell_script_with_os(utils_sh_file, "init"):
                logger.warning("环境初始化可能不完整")
        except Exception as e:
            logger.warning(f"环境初始化出错: {str(e)}")

        # 生成ed25519密钥对
        if utils.prompt_user_input("生成私钥(一般是安装面板需要生成，安装agent时不需要)"):
            try:
                if not gen_ed25519(utils_sh_file, ssh_dir):
                    logger.warning("生成密钥对失败")
            except Exception as e:
                logger.warning(f"生成密钥对时出错: {str(e)}")

        # 初始化配置并连接所有主机
        logger.info("===> 开始连接host.conf中配置的相互保活的主机....")
        config_entries = []
        try:
            if os.path.exists(host_config_file):
                host_config = HostConfigEntry(host_config_file, private_key_file)
                config_entries = host_config.get_entries()
                logger.info(f"已加载{len(config_entries)}个主机配置")
            else:
                logger.warning(f"主机配置文件不存在: {host_config_file}")
        except Exception as e:
            logger.warning(f"加载主机配置失败: {str(e)}")

        # sshd公私钥文件拷贝
        if config_entries and utils.prompt_user_input("拷贝公私钥到相互保活的主机(一般是首次安装面板才需要)"):
            try:
                await transfer_ssh_dir_to_all_hosts(config_entries, host_name, user_name, ssh_dir)
            except Exception as e:
                logger.warning(f"拷贝SSH密钥时出错: {str(e)}")

        # 生成所有主机的保活配置
        try:
            await gen_all_hosts_heart_beat_config(utils_sh_file, heart_beat_config_file, config_entries, host_name, user_name)
        except Exception as e:
            logger.warning(f"生成心跳配置时出错: {str(e)}")

        # 安装选择
        logger.info("\n请选择安装选项:")
        logger.info("1. 安装哪吒面板")
        logger.info("2. 安装agent客户端")
        logger.info("3. 安装面板+agent")
        logger.info("4. 清理哪吒面板")
        logger.info("5. 清理Agent")
        logger.info("0. 退出")

        nezha_opt = input("请输入选项编号: ")
        try:
            if nezha_opt == "1":
                utils.run_shell_script_with_os(utils_sh_file, "install", "dashboard", dashboard_dir, monitor_config_file)
            elif nezha_opt == "2":
                utils.run_shell_script_with_os(utils_sh_file, "install", "agent", agent_dir, monitor_config_file)
            elif nezha_opt == "3":
                utils.run_shell_script_with_os(utils_sh_file, "install", "both", utils.get_app_dir(user_name), monitor_config_file)
            elif nezha_opt == "4":
                if utils.prompt_user_input("确认清理哪吒面板"):
                    utils.run_shell_script_with_os(utils_sh_file, "clean", "dashboard", dashboard_dir)
            elif nezha_opt == "5":
                if utils.prompt_user_input("确认清理Agent"):
                    utils.run_shell_script_with_os(utils_sh_file, "clean", "agent", agent_dir)
            else:
                logger.info("已取消操作")
        except Exception as e:
            logger.error(f"执行安装/清理操作失败: {str(e)}")

        logger.info("=======> 安装结束")

    except KeyboardInterrupt:
        logger.info("操作被用户中断")
    except Exception as e:
        error_message = f"程序执行出错: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())

@utils.time_count
def main():
    # 设置信号处理
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGHUP, handle_shutdown_signal)

    try:
        asyncio.run(main_async())
    except Exception as e:
        logger.error(f"主程序异常: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())