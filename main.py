#!/usr/bin/env python3
import os
import sys
from time import sleep
from typing import List, Dict, Optional
import asyncio
import signal
import traceback

# 确保 src 目录在系统路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.config.host_config_entry import HostConfigEntry
from src.config.sys_config_entry import SysConfigEntry
from src.utils.async_utils import AsyncExecutor
import src.utils.utils as utils
from src.utils.logger_wrapper import LoggerWrapper

# 初始化全局日志记录器
logger = LoggerWrapper()

# 全局变量
shutdown_event = asyncio.Event()

# 设置信号处理函数，优雅退出
def handle_shutdown_signal(signum, frame):
    print(f"\n收到信号 {signum}，正在优雅退出...")
    shutdown_event.set()

async def transfer_ssh_file_to_host(entry: Dict, host_name: str, user_name: str, local_dir: str, host_id: int) -> None:
    """向单个主机传输SSH文件"""
    client = entry.get('client')
    if not client:
        print(f"==> [{host_id}]号主机未连接成功 [{entry['username']}@{entry['hostname']}:{entry['port']}]")
        return

    if entry['hostname'] == host_name and entry['username'] == user_name:
        print(f"==> [{host_id}]号主机为当前主机，不需要处理")
        return

    print(f"==> 开始拷贝到[{host_id}]号主机 [{entry['username']}@{entry['hostname']}:{entry['port']}]...")
    try:
        remote_dir = utils.get_ssh_dir(entry['username'])
        await AsyncExecutor.run_in_thread(client.transfer_files, local_dir, remote_dir)
        print(f"==> [{host_id}]号主机文件拷贝成功")
    except Exception as e:
        error_msg = f"拷贝文件到[{host_id}]号主机失败: {str(e)}"
        print(f"错误: {error_msg}")
        logger.error(error_msg)

async def transfer_ssh_dir_to_all_hosts(config_entries: List[Dict], host_name: str, user_name: str, local_dir: str) -> None:
    """异步并行向所有主机传输SSH目录"""
    tasks = []
    for host_id, entry in enumerate(config_entries, 1):
        task = transfer_ssh_file_to_host(entry, host_name, user_name, local_dir, host_id)
        tasks.append(task)

    # 并行执行所有传输任务，最多3个并发，忽略单个失败
    await AsyncExecutor.gather_with_concurrency(3, *tasks, ignore_exceptions=True)

async def gen_host_heart_beat_config(utils_sh_file: str, heart_beat_config_file: str, entry: Dict,
                                     host_name: str, user_name: str, host_id: int) -> None:
    """为单个主机生成心跳配置"""
    if host_name == entry["hostname"] and user_name == entry["username"]:
        print(f"====> [{host_id}]号主机[{user_name}@{host_name}]是当前主机，跳过不处理")
        return

    print(f"====> 开始把[{host_id}]号主机[{entry['username']}@{entry['hostname']}]写入到心跳配置文件中{heart_beat_config_file}")
    try:
        result = await AsyncExecutor.run_in_thread(
            utils.run_shell_script_with_os,
            utils_sh_file, 'heart', heart_beat_config_file, entry["hostname"],
            str(entry["port"]), entry["username"]
        )
        if not result:
            error_msg = f"警告: 写入[{host_id}]号主机信息失败"
            print(error_msg)
            logger.warning(error_msg)
    except Exception as e:
        error_msg = f"错误: 写入[{host_id}]号主机信息时发生异常: {str(e)}"
        print(error_msg)
        logger.error(error_msg)

async def gen_all_hosts_heart_beat_config(utils_sh_file: str, heart_beat_config_file: str, config_entries: List[Dict],
                                         host_name: str, user_name: str) -> None:
    """异步并行为所有主机生成心跳配置"""
    print(f"==> 开始把所有主机信息写入到心跳配置文件中{heart_beat_config_file}")

    tasks = []
    for host_id, entry in enumerate(config_entries, 1):
        task = gen_host_heart_beat_config(
            utils_sh_file, heart_beat_config_file, entry,
            host_name, user_name, host_id
        )
        tasks.append(task)

    # 并行执行所有配置生成任务，忽略单个任务失败
    await AsyncExecutor.gather_with_concurrency(5, *tasks, ignore_exceptions=True)

def gen_ed25519(utils_sh_file: str, ssh_dir: str) -> bool:
    """
    生成ED25519 SSH密钥对
    
    Args:
        utils_sh_file: 工具脚本路径
        ssh_dir: SSH配置目录
        
    Returns:
        bool: 是否成功生成
    """
    print(f"===> 开始生成ed25519密钥对，密钥保存在{ssh_dir}目录...")
    return utils.run_shell_script_with_os(utils_sh_file, "keygen", ssh_dir)

@utils.time_count
async def main_async():
    """异步主函数"""
    try:
        host_name, user_name = utils.get_hostname_and_username()
        print(f"===> 当前主机: {host_name}, 用户: {user_name}")

        # 定义环境
        ssh_dir = utils.get_ssh_dir(user_name)
        private_key_file = utils.get_ssh_ed25519_pri(user_name)

        # 应用安装目录
        dashboard_dir = utils.get_dashboard_dir(user_name)
        agent_dir = utils.get_agent_dir(user_name)

        # 当前脚本所在的目录
        serv00_ct8_dir = os.path.dirname(os.path.abspath(__file__))
        utils_sh_file = utils.get_serv00_dir_file(serv00_ct8_dir, 'scripts/utils.sh')

        # 检查utils.sh脚本是否存在
        if not os.path.exists(utils_sh_file):
            print(f"错误: 工具脚本不存在: {utils_sh_file}")
            return

        # 生成配置文件
        print(f"===> 从[config]目录生成配置文件...")
        if not utils.run_shell_script_with_os(utils_sh_file, 'rename_config', utils.get_serv00_config_dir(serv00_ct8_dir)):
            print(f"===> 从[config]目录生成配置文件失败，请检查serv00是否开启允许应用....")
            return

        print(f"===> 从[config]目录生成配置文件成功....")

        sys_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'sys.conf')
        host_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'host.conf')
        monitor_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'monitor.conf')
        heart_beat_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'heartbeat.conf')

        # 加载系统配置
        SysConfigEntry(sys_config_file)

        # 初始化
        utils.run_shell_script_with_os(utils_sh_file, "init")

        # 生成ed25519密钥对
        if utils.prompt_user_input("生成私钥(一般是安装面板需要生成，安装agent时不需要)"):
            if not gen_ed25519(utils_sh_file, ssh_dir):
                print("警告: 生成密钥对失败，但将继续执行后续步骤")

        # 初始化配置并连接所有主机
        print("===> 开始连接host.conf中配置的相互保活的主机....")
        host_config = HostConfigEntry(host_config_file, private_key_file)
        config_entries = host_config.get_entries()

        # sshd公私钥文件拷贝
        if utils.prompt_user_input("拷贝公私钥到相互保活的主机(一般是首次安装面板才需要)"):
            await transfer_ssh_dir_to_all_hosts(config_entries, host_name, user_name, ssh_dir)

        # 生成所有主机的保活配置
        await gen_all_hosts_heart_beat_config(utils_sh_file, heart_beat_config_file, config_entries, host_name, user_name)

        # 安装选择
        nezha_opt = input("请选择安装选项(1.安装哪吒面板 2.安装agent客户端 3.安装面板+agent 4.清理哪吒面板 5.清理Agent 0.退出): ")
        if nezha_opt == "1":
            utils.run_shell_script_with_os(utils_sh_file, "install", "dashboard", dashboard_dir, monitor_config_file)
        elif nezha_opt == "2":
            utils.run_shell_script_with_os(utils_sh_file, "install", "agent", agent_dir, monitor_config_file)
        elif nezha_opt == "3":
            utils.run_shell_script_with_os(utils_sh_file, "install", "both", utils.get_app_dir(user_name), monitor_config_file)
        elif nezha_opt == "4":
            utils.run_shell_script_with_os(utils_sh_file, "clean", "dashboard", dashboard_dir)
        elif nezha_opt == "5":
            utils.run_shell_script_with_os(utils_sh_file, "clean", "agent", agent_dir)

        print("=======> 安装结束")
        
    except KeyboardInterrupt:
        print("\n操作被用户中断")
    except Exception as e:
        error_message = f"程序执行出错: {str(e)}"
        print(f"错误: {error_message}")
        print(f"堆栈跟踪: {traceback.format_exc()}")
        logger.error(error_message)
        logger.error(traceback.format_exc())

@utils.time_count
def main():
    """同步入口函数，启动异步事件循环"""
    # 设置信号处理，支持优雅退出
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        asyncio.run(main_async())
    except Exception as e:
        print(f"主程序异常: {str(e)}")
        logger.error(f"主程序异常: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())