import os
import socket
import shlex
import functools
from time import time
from getpass import getuser
import logging

# 初始化日志记录器
# 避免使用 from logger_wrapper import LoggerWrapper 避免循环导入
from .logger_wrapper import LoggerWrapper

# 当前模块使用的logger
logger = LoggerWrapper()

def time_count(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        elapsed_time = end_time - start_time

        if elapsed_time < 60:
            print(f"=======> 函数 {func.__name__} 总共耗时: {elapsed_time:.2f} 秒")
        else:
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            print(f"=======> 函数 {func.__name__} 总共耗时: {int(minutes)} 分 {seconds:.2f} 秒")

        return result
    return wrapper

def get_shell_run_cmd(shell_path, *args):
    quoted_args = [shlex.quote(str(arg)) for arg in args]
    return f'{shell_path} {" ".join(quoted_args)}'

def run_shell_script_with_os(shell_path, *args):
    cmd = get_shell_run_cmd(shell_path, *args)
    try:
        result = os.system(cmd)
        if result == 0:
            logger.info(f"Shell command executed successfully: {cmd}")
            return True
        else:
            logger.error(f"Shell command execution failed with exit code {result}: {cmd}")
            return False
    except Exception as e:
        logger.error(f"Shell command execution error: {cmd}, error: {str(e)}")
        return False

def overwrite_msg_to_file(msg, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(str(msg))
        return True
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {str(e)}")
        return False

def get_hostname_and_username():
    hostname = socket.gethostname()
    try:
        username = os.getlogin()
    except OSError:
        username = getuser()
    return hostname, username

def get_user_home_dir(user_name):
    return os.path.join('/home', user_name)

def get_ssh_dir(user_name):
    return os.path.join(get_user_home_dir(user_name), '.ssh')

def get_app_dir(user_name):
    return os.path.join(get_user_home_dir(user_name), 'nezha_app')

def get_dashboard_dir(user_name):
    return os.path.join(get_app_dir(user_name), 'dashboard')

def get_dashboard_config_file(user_name):
    config_dir = get_dashboard_dir(user_name)
    return os.path.join(config_dir, 'data/config.yaml')

def get_dashboard_db_file(user_name):
    dashboard_dir = get_dashboard_dir(user_name)
    return os.path.join(dashboard_dir, 'data/sqlite.db')

def get_agent_dir(user_name):
    return os.path.join(get_app_dir(user_name), 'agent')

def get_ssh_ed25519_pri(user_name):
    ssh_dir = get_ssh_dir(user_name)
    return os.path.expanduser(os.path.join(ssh_dir, 'id_ed25519'))

def get_serv00_config_dir(serv00_ct8_dir):
    return os.path.join(serv00_ct8_dir, 'config')

def get_serv00_config_file(serv00_ct8_dir, file_name):
    config_dir = get_serv00_config_dir(serv00_ct8_dir)
    return os.path.join(config_dir, file_name)

def get_serv00_dir_file(serv00_ct8_dir, file_name):
    return os.path.join(serv00_ct8_dir, file_name)

def check_file_exists(file_path):
    return os.path.exists(file_path)

def parse_heart_beat_extra_info(info):
    if not info:
        return None

    parts = info.split('|')
    if len(parts) != 4:
        return None

    opt, hostname, port, username = parts
    try:
        return {
            "type": opt,
            "hostname": hostname,
            "port": int(port),
            "username": username
        }
    except ValueError:
        logger.error(f"Invalid heart beat info format: {info}")
        return None

def make_heart_beat_extra_info(info, host_name, user_name):
    if not info:
        return f"0|{host_name}|22|{user_name}"

    return f"0|{info['hostname']}|{info['port']}|{info['username']}"

def need_check_and_heart_beat(heat_beat_extra_info):
    # 自身定时任务执行
    if not heat_beat_extra_info:
        return True

    return heat_beat_extra_info.get('type') != "0"

def prompt_user_input(msg):
    valid_inputs = {'y', 'n'}

    while True:
        try:
            user_input = input(f"是否{msg}? (y/n): ").strip().lower()

            if user_input in valid_inputs:
                return user_input == 'y'
            else:
                logger.info("无效输入，请输入 Y 或者 y 执行，N 或者 n 不执行")
        except KeyboardInterrupt:
            print("\n操作已取消")
            return False
        except Exception as e:
            logger.error(f"获取用户输入出错: {str(e)}")
            return False
