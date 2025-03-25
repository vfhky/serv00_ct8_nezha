#!/usr/bin/env python3
import os
import socket
import asyncio
from datetime import datetime
from typing import Dict, Optional, Set, List, Tuple

import requests
import pytz

from ..config.heart_beat_config_entry import HeartBeatConfigEntry
from ..config.sys_config_entry import SysConfigEntry
from ..utils.logger_wrapper import LoggerWrapper
from ..utils.async_utils import AsyncExecutor
import src.utils.utils as utils
from ..notify.notify_entry import NotifyEntry
from ..backup.backup_entry import BackupEntry

# 常量定义
TIMEOUT = 3
HTTP_OK = 200

# 初始化日志记录器
logger = LoggerWrapper()

# Setup script directories and files
SERV00_CT8_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT_TMP_DIR = utils.get_serv00_dir_file(SERV00_CT8_DIR, "tmp")
os.makedirs(SCRIPT_TMP_DIR, exist_ok=True)
OK_NOTIFY_HOUR_FILE = os.path.join(SCRIPT_TMP_DIR, 'ok_notify_hour_file')

def parse_ok_notify_hours(hours_str: str) -> Optional[Set[int]]:
    return {int(hour.strip()) for hour in hours_str.split(',')} if hours_str else None

def check_and_write_notify_hour_file(file_path: str, ok_notify_hours: Optional[Set[int]]) -> bool:
    current_hour = datetime.now(pytz.timezone('Asia/Shanghai')).hour

    if ok_notify_hours is None or current_hour in ok_notify_hours:
        try:
            with open(file_path, "r") as file:
                if int(file.read().strip()) == current_hour:
                    return False
        except (FileNotFoundError, ValueError):
            pass

        utils.overwrite_msg_to_file(str(current_hour), file_path)
        return True

    logger.info(f"当前时间{current_hour}不需要发起通知")
    return False

def check_monitor_url_dns(url: str, notifier: NotifyEntry) -> bool:
    try:
        logger.info(f"==> 开始检测监控域名[{url}]的DNS解析情况")
        host = socket.gethostbyname(url.split('/')[2])
        logger.info(f"==> 监控域名[{url}]解析成功，IP地址为: {host}")
        return True
    except socket.gaierror as e:
        notifier.check_monitor_url_dns_fail_notify(url, e)
        return False

def check_monitor_url_visit(url: str, notifier: NotifyEntry, sys_config_entry: SysConfigEntry) -> bool:
    try:
        logger.info(f"==> 开始检测监控域名{url}的访问状态")
        with requests.get(url, timeout=TIMEOUT) as response:
            logger.info(f"监控域名{url}的访问状态为: {response.status_code}")

            if response.status_code != HTTP_OK:
                notifier.check_monitor_url_visit_fail_notify(url, response)
            else:
                ok_notify_hours = sys_config_entry.get("OK_NOTIFY_HOURS")
                if check_and_write_notify_hour_file(OK_NOTIFY_HOUR_FILE, parse_ok_notify_hours(ok_notify_hours)):
                    notifier.check_monitor_url_visit_ok_notify(url, response)

            return response.status_code == HTTP_OK
    except requests.RequestException as e:
        logger.error(f"==> 异常: {e}")
        notifier.check_monitor_url_visit_fail_notify(url, str(e))
        return False

def check_monitor_url(url: str, notifier: NotifyEntry, sys_config_entry: SysConfigEntry) -> bool:
    if not check_monitor_url_dns(url, notifier):
        return False
    return check_monitor_url_visit(url, notifier, sys_config_entry)

async def process_host_heart_beat(entry: Dict, heart_beat_entry_file: str, heart_beat_extra_info: Dict,
                                  local_host_name: str, local_user_name: str, host_id: int) -> None:
    """处理单个主机的心跳"""
    client = entry.get('client')
    hostname = entry.get('hostname')
    username = entry.get('username')

    if hostname == local_host_name and username == local_user_name:
        logger.info(f"==> [{host_id}]号主机[{username}@{hostname}]是当前主机，跳过不处理")
        return

    if client:
        logger.info(f"==> 开始维护[{host_id}]号主机[{username}@{hostname}]的心跳...")
        remote_heart_beat_entry_file = heart_beat_entry_file.replace(local_user_name, username)
        param = utils.make_heart_beat_extra_info(heart_beat_extra_info, hostname, username)
        try:
            result = await AsyncExecutor.run_in_thread(
                client.ssh_exec_script,
                remote_heart_beat_entry_file,
                param
            )
            if not result:
                logger.warning(f"==> 维护[{host_id}]号主机[{username}@{hostname}]的心跳失败")
        except Exception as e:
            logger.error(f"==> 维护[{host_id}]号主机[{username}@{hostname}]的心跳时发生异常: {str(e)}")
    else:
        logger.error(f"==> 维护远程主机[{host_id}]号主机[{username}@{hostname}]失败, 初始化配置的时候连接异常")

async def all_host_make_heart_beat(config_entries: List[Dict], heart_beat_entry_file: str,
                                  heart_beat_extra_info: Dict, local_host_name: str, local_user_name: str) -> None:
    """异步并行处理所有主机的心跳"""
    tasks = []

    for host_id, entry in enumerate(config_entries, 1):
        task = process_host_heart_beat(
            entry, heart_beat_entry_file, heart_beat_extra_info,
            local_host_name, local_user_name, host_id
        )
        tasks.append(task)

    # 并行执行所有心跳任务，最多5个并发
    await AsyncExecutor.gather_with_concurrency(5, *tasks)

def load_configurations(serv00_ct8_dir: str) -> Tuple[SysConfigEntry, str]:
    sys_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'sys.conf')
    heart_beat_config_file = utils.get_serv00_config_file(serv00_ct8_dir, 'heartbeat.conf')
    return SysConfigEntry(sys_config_file), heart_beat_config_file

async def main_async() -> None:
    """异步主函数"""
    try:
        logger.info("==================== 开始心跳模块 ====================")

        host_name, user_name = utils.get_hostname_and_username()
        private_key_file = utils.get_ssh_ed25519_pri(user_name)

        heat_beat_extra_info = utils.parse_heart_beat_extra_info(os.environ.get('HEART_BEAT_EXTRA_INFO'))
        msg = (f"==> 心跳来自主机[{heat_beat_extra_info['username']}@{heat_beat_extra_info['hostname']}:{heat_beat_extra_info['port']}] 类型:{heat_beat_extra_info['type']}"
               if heat_beat_extra_info else
               f"==> 心跳来自当前主机自身[{user_name}@{host_name}] heat_beat_extra_info={heat_beat_extra_info}")
        logger.info(msg)

        sys_config_entry, heart_beat_config_file = load_configurations(SERV00_CT8_DIR)
        notifier = NotifyEntry(sys_config_entry)

        process_monitor_file = utils.get_serv00_dir_file(SERV00_CT8_DIR, 'process_monitor.sh')
        monitor_config_file = utils.get_serv00_config_file(SERV00_CT8_DIR, 'monitor.conf')
        logger.info(f"==> 开始启动进程，[{process_monitor_file}] [{monitor_config_file}]")
        if not utils.run_shell_script_with_os(process_monitor_file, monitor_config_file):
            logger.error(f"====> 启动进程失败")

        heart_beat_entry_file = utils.get_serv00_dir_file(SERV00_CT8_DIR, 'heart_beat_entry.sh')
        utils_sh_file = utils.get_serv00_dir_file(SERV00_CT8_DIR, 'utils.sh')
        logger.info(f"==> 开始设置心跳的crontab，[{heart_beat_entry_file}]")
        if not utils.run_shell_script_with_os(utils_sh_file, "cron", sys_config_entry.get('HEAT_BEAT_CRON_TABLE_TIME'), heart_beat_entry_file):
            logger.error(f"====> 设置失败")

        if utils.need_check_and_heart_beat(heat_beat_extra_info):
            if sys_config_entry.get('CHECK_MONITOR_URL_DNS') == "1":
                check_monitor_url(sys_config_entry.get('MONITOR_URL'), notifier, sys_config_entry)

            logger.info(f"==> 开始读取心跳配置文件[{heart_beat_config_file}]...")
            heart_beat_config = HeartBeatConfigEntry(heart_beat_config_file, private_key_file)
            heart_config_entries = heart_beat_config.get_entries()

            # 异步处理所有主机的心跳
            await all_host_make_heart_beat(
                heart_config_entries, heart_beat_entry_file,
                heat_beat_extra_info, host_name, user_name
            )

        backup_entry = BackupEntry(sys_config_entry)
        dashboard_db_file = utils.get_dashboard_db_file(user_name)

        # 异步执行备份
        await backup_entry.backup_dashboard_db_async(dashboard_db_file)

    except Exception as e:
        logger.error(f"心跳模块运行时出现未预期的错误: {str(e)}")
    finally:
        logger.info(f"==============> 结束心跳模块 <==============")

def main() -> None:
    """同步入口函数，启动异步事件循环"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()