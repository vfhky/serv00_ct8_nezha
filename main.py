#!/usr/bin/env python3
import os
import sys
from time import sleep
from typing import List, Dict
import asyncio

# 确保 src 目录在系统路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config.host_config_entry import HostConfigEntry
from src.config.sys_config_entry import SysConfigEntry
from src.utils.async_utils import AsyncExecutor
import src.utils.utils as utils

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
    remote_dir = utils.get_ssh_dir(entry['username'])
    await AsyncExecutor.run_in_thread(client.transfer_files, local_dir, remote_dir)

async def transfer_ssh_dir_to_all_hosts(config_entries: List[Dict], host_name: str, user_name: str, local_dir: str) -> None:
    """异步并行向所有主机传输SSH目录"""
    tasks = []
    for host_id, entry in enumerate(config_entries, 1):
        task = transfer_ssh_file_to_host(entry, host_name, user_name, local_dir, host_id)
        tasks.append(task)

    # 并行执行所有传输任务，最多3个并发
    await AsyncExecutor.gather_with_concurrency(3, *tasks)

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
            print(f"警告: 写入[{host_id}]号主机信息失败")
    except Exception as e:
        print(f"错误: 写入[{host_id}]号主机信息时发生异常: {str(e)}")

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

    # 并行执行所有配置生成任务
    await asyncio.gather(*tasks)

# ... 其他函数 ...

@utils.time_count
async def main_async():
    """异步主函数"""
    host_name, user_name = utils.get_hostname_and_username()

    # 定义环境
    ssh_dir = utils.get_ssh_dir(user_name)
    private_key_file = utils.get_ssh_ed25519_pri(user_name)

    # 应用安装目录
    dashboard_dir = utils.get_dashboard_dir(user_name)
    agent_dir = utils.get_agent_dir(user_name)

    # 当前脚本所在的目录
    serv00_ct8_dir = os.path.dirname(os.path.abspath(__file__))
    utils_sh_file = utils.get_serv00_dir_file(serv00_ct8_dir, 'scripts/utils.sh')

    # 生成配置文件
    if not utils.run_shell_script_with_os(utils_sh_file, 'rename_config', utils.get_serv00_config_dir(serv00_ct8_dir)):
        print(f"===> 从[config]目录生成配置文件失败，请检查serv00是否开启允许应用....")
        sys.exit(1)

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
        gen_ed25519(utils_sh_file, ssh_dir)

    # 初始化配置并连接所有主机
    print("===> 开始连接host.conf中配置的相互保活的主机....")
    host_config = HostConfigEntry(host_config_file, private_key_file)
    config_entries = host_config.get_entries()

    # sshd公私钥文件拷贝
    if utils.prompt_user_input("拷贝公私钥到相互保活的主机(一般是首次安装面板才需要)"):
        await transfer_ssh_dir_to_all_hosts(config_entries, host_name, user_name, ssh_dir)

    # ... 安装和配置部分 ...

    # 生成所有主机的保活配置
    await gen_all_hosts_heart_beat_config(utils_sh_file, heart_beat_config_file, config_entries, host_name, user_name)

    print("=======> 安装结束")

@utils.time_count
def main():
    """同步入口函数，启动异步事件循环"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()