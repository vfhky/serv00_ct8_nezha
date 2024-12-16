#!/usr/bin/env python3
import os
import sys
from time import sleep
from typing import List, Dict
from host_config_entry import HostConfigEntry
from sys_config_entry import SysConfigEntry
import utils


def gen_ed25519(utils_sh_file: str, ssh_dir: str) -> None:
    if not utils.run_shell_script_with_os(utils_sh_file, 'init') or not utils.run_shell_script_with_os(utils_sh_file, 'key'):
        print("生成公私钥失败，请检查~/.ssh/目录")
        sys.exit(1)

    ed25519_files = {
        'pub': f'{ssh_dir}/id_ed25519.pub',
        'private': f'{ssh_dir}/id_ed25519',
        'auth': f'{ssh_dir}/authorized_keys'
    }

    if not all(utils.check_file_exists(os.path.expanduser(file)) for file in ed25519_files.values()):
        print("公私钥缺失异常，请检查~/.ssh/目录")
        sys.exit(1)


def transfer_ssh_dir_to_all_hosts(config_entries: List[Dict], host_name: str, user_name: str, local_dir: str) -> None:
    for host_id, entry in enumerate(config_entries, 1):
        client = entry.get('client')
        if not client:
            print(f"==> [{host_id}]号主机未连接成功 [{entry['username']}@{entry['hostname']}:{entry['port']}]")
            continue

        if entry['hostname'] == host_name and entry['username'] == user_name:
            print(f"==> [{host_id}]号主机为当前主机，不需要处理")
            continue

        print(f"==> 开始拷贝到[{host_id}]号主机 [{entry['username']}@{entry['hostname']}:{entry['port']}]...")
        remote_dir = utils.get_ssh_dir(entry['username'])
        client.transfer_files(local_dir, remote_dir)


def gen_nezha_monitor_config(utils_sh_file: str, monitor_config_file: str, nezha_dir: str, process_name: str,
                             process_run: str, process_run_mode: str) -> None:
    print(f"====> 开始把进程[{process_name}]写入到监控配置文件中{monitor_config_file}")
    utils.run_shell_script_with_os(utils_sh_file, 'monitor', monitor_config_file, nezha_dir, process_name,
                                   process_run, process_run_mode)


def gen_all_hosts_heart_beat_config(utils_sh_file: str, heart_beat_config_file: str, config_entries: List[Dict],
                                    host_name: str, user_name: str) -> None:
    print(f"==> 开始把所有主机信息写入到心跳配置文件中{heart_beat_config_file}")
    for host_id, entry in enumerate(config_entries, 1):
        if host_name == entry["hostname"] and user_name == entry["username"]:
            print(f"====> [{host_id}]号主机[{user_name}@{host_name}]是当前主机，跳过不处理")
            continue
        print(f"====> 开始把[{host_id}]号主机[{entry['username']}@{entry['hostname']}]写入到心跳配置文件中{heart_beat_config_file}")
        try:
            result = utils.run_shell_script_with_os(utils_sh_file, 'heart', heart_beat_config_file, entry["hostname"],
                                                    str(entry["port"]), entry["username"])
            if not result:
                print(f"警告: 写入[{host_id}]号主机信息失败")
        except Exception as e:
            print(f"错误: 写入[{host_id}]号主机信息时发生异常: {str(e)}")


def start_process(serv00_ct8_dir: str, host_name: str, user_name: str) -> None:
    # 通过进程监控配置文件，开启进程
    print("===> 开始通过进程监控配置文件，开启进程....")
    heart_beat_entry_file = utils.get_serv00_dir_file(serv00_ct8_dir, 'heart_beat_entry.sh')
    param = utils.make_heart_beat_extra_info(None, host_name, user_name)
    utils.run_shell_script_with_os(heart_beat_entry_file, param)

@utils.time_count
def main():
    host_name, user_name = utils.get_hostname_and_username()

    # 定义环境
    ssh_dir = utils.get_ssh_dir(user_name)
    private_key_file = utils.get_ssh_ed25519_pri(user_name)

    # 应用安装目录
    dashboard_dir = utils.get_dashboard_dir(user_name)
    agent_dir = utils.get_agent_dir(user_name)

    # 当前脚本所在的目录
    serv00_ct8_dir = os.path.dirname(os.path.abspath(__file__))
    utils_sh_file = utils.get_serv00_dir_file(serv00_ct8_dir, 'utils.sh')

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
    print("===> 开始读取host.conf主机配置文件....")
    host_config = HostConfigEntry(host_config_file, private_key_file)
    config_entries = host_config.get_entries()

    # sshd公私钥文件拷贝
    if utils.prompt_user_input("拷贝公私钥文件到各个主机(一般是安装面板需要生成，安装agent时不需要)"):
        transfer_ssh_dir_to_all_hosts(config_entries, host_name, user_name, ssh_dir)

    if utils.prompt_user_input("选择安装哪吒V1版本？(V1和V0完全不兼容，请确认)"):
        download_nezha_sh = utils.get_serv00_dir_file(serv00_ct8_dir, 'download_nezha_v1.sh')
        print("===> 您选择安装哪吒V1版本。")
    else:
        download_nezha_sh = utils.get_serv00_dir_file(serv00_ct8_dir, 'download_nezha.sh')
        print("===> 您选择安装哪吒V0版本。")

    if utils.prompt_user_input("开始安装哪吒dashboard"):
        print("===> 开始安装哪吒dashboard....")
        if not utils.run_shell_script_with_os(download_nezha_sh, "dashboard", dashboard_dir):
            print("===> 安装失败，请稍后再重试....")
            sys.exit(1)

        gen_nezha_monitor_config(utils_sh_file, monitor_config_file, dashboard_dir,
                                        "nezha-dashboard",
                                        "./nezha-dashboard", "background")
        utils.run_shell_script_with_os(utils_sh_file, "check", "1", sys_config_file)

        start_process(serv00_ct8_dir, host_name, user_name)
        sleep(2)
        utils.run_shell_script_with_os(utils_sh_file, "show_agent_key", utils.get_dashboard_config_file(user_name))

    if utils.prompt_user_input("开始安装哪吒agent"):
        print("===> 开始安装哪吒agent....")
        if not utils.run_shell_script_with_os(download_nezha_sh, "agent", agent_dir):
            print("===> 安装失败，请稍后再重试....")
            sys.exit(1)

        gen_nezha_monitor_config(utils_sh_file, monitor_config_file, agent_dir, "nezha-agent", 
                                 "sh nezha-agent.sh", "foreground")
        start_process(serv00_ct8_dir, host_name, user_name)

    # 生成所有主机的保活配置
    gen_all_hosts_heart_beat_config(utils_sh_file, heart_beat_config_file, config_entries, host_name, user_name)

    print("=======> 安装结束....")


if __name__ == '__main__':
    main()
