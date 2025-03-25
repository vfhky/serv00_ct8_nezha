import os
import socket
import shlex
import functools
import stat
from time import time
from getpass import getuser
import logging
import subprocess

# 避免使用 from logger_wrapper import LoggerWrapper 避免循环导入
from .logger_wrapper import LoggerWrapper

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

def run_shell_script_with_subprocess(shell_path, *args, capture_output=False, timeout=60):
    cmd = [shell_path] + list(args)
    try:
        if not os.path.exists(shell_path):
            logger.error(f"脚本文件不存在: {shell_path}")
            return False, None

        # 确保脚本有执行权限
        ensure_file_permissions(shell_path, 0o755)

        if capture_output:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, timeout=timeout)
            return True, result.stdout
        else:
            subprocess.run(cmd, check=True, timeout=timeout)
            return True, None
    except subprocess.TimeoutExpired:
        error_msg = f"命令执行超时 ({timeout}秒): {cmd}"
        logger.error(error_msg)
        return False, error_msg
    except subprocess.CalledProcessError as e:
        error_msg = f"命令执行失败: {e}, 退出码: {e.returncode}"
        logger.error(error_msg)
        if capture_output:
            return False, e.stderr
        else:
            return False, error_msg
    except Exception as e:
        error_msg = f"命令执行错误: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def overwrite_msg_to_file(msg, file_path):
    try:
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            os.chmod(dir_path, 0o755)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(str(msg))

        os.chmod(file_path, 0o644)
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
    ssh_dir = os.path.join(get_user_home_dir(user_name), '.ssh')

    # 确保目录存在
    if not os.path.exists(ssh_dir):
        try:
            os.makedirs(ssh_dir, exist_ok=True)
            # SSH目录需要700权限
            os.chmod(ssh_dir, 0o700)
        except Exception as e:
            logger.error(f"创建SSH目录失败: {str(e)}")

    return ssh_dir

def get_app_dir(user_name):
    app_dir = os.path.join(get_user_home_dir(user_name), 'nezha_app')

    if not os.path.exists(app_dir):
        try:
            os.makedirs(app_dir, exist_ok=True)
            os.chmod(app_dir, 0o755)
        except Exception as e:
            logger.error(f"创建应用目录失败: {str(e)}")

    return app_dir

def get_dashboard_dir(user_name):
    return os.path.join(get_app_dir(user_name), 'dashboard')

def get_dashboard_config_file(user_name):
    config_dir = get_dashboard_dir(user_name)
    return os.path.join(config_dir, 'data', 'config.yaml')

def get_dashboard_db_file(user_name):
    dashboard_dir = get_dashboard_dir(user_name)
    return os.path.join(dashboard_dir, 'data', 'sqlite.db')

def get_agent_dir(user_name):
    return os.path.join(get_app_dir(user_name), 'agent')

def get_ssh_ed25519_pri(user_name):
    ssh_dir = get_ssh_dir(user_name)
    private_key_file = os.path.join(ssh_dir, 'id_ed25519')

    # 检查私钥权限
    if os.path.exists(private_key_file):
        try:
            current_mode = os.stat(private_key_file).st_mode
            if (current_mode & 0o777) != 0o600:
                logger.warning(f"私钥文件权限不正确，正在修复: {private_key_file}")
                os.chmod(private_key_file, 0o600)
        except Exception as e:
            logger.error(f"无法设置私钥文件权限: {str(e)}")

    return private_key_file

def get_serv00_config_dir(serv00_ct8_dir):
    return os.path.join(serv00_ct8_dir, 'config')

def get_serv00_config_file(serv00_ct8_dir, file_name):
    config_dir = get_serv00_config_dir(serv00_ct8_dir)
    return os.path.join(config_dir, file_name)

def get_serv00_dir_file(serv00_ct8_dir, file_name):
    return os.path.join(serv00_ct8_dir, file_name)

def check_file_exists(file_path):
    return os.path.exists(file_path)

def ensure_file_permissions(file_path, permission=0o644):
    try:
        if not os.path.exists(file_path):
            # 检查父目录是否存在
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                os.chmod(parent_dir, 0o755)
                logger.info(f"创建目录并设置权限: {parent_dir}")
            return False

        current_mode = os.stat(file_path).st_mode
        if (current_mode & 0o777) != permission:
            logger.info(f"修正文件权限: {file_path}")
            os.chmod(file_path, permission)
        return True
    except Exception as e:
        logger.error(f"设置文件权限失败: {str(e)}")
        return False

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
