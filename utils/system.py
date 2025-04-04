import os
import socket
import shlex
import subprocess
from getpass import getuser
from typing import List, Tuple, Optional, Any
from utils.logger import get_logger

logger = get_logger()

def get_hostname_and_username() -> Tuple[str, str]:
    """
    获取当前主机名和用户名

    Returns:
        Tuple[str, str]: 主机名和用户名的元组
    """
    hostname = socket.gethostname()
    try:
        username = os.getlogin()
    except OSError:
        username = getuser()
    return hostname, username

def get_user_home_dir(user_name: str) -> str:
    """
    获取用户的家目录

    Args:
        user_name: 用户名

    Returns:
        str: 用户家目录路径
    """
    return os.path.join('/home', user_name)

def get_ssh_dir(user_name: str) -> str:
    """
    获取用户的SSH目录

    Args:
        user_name: 用户名

    Returns:
        str: SSH目录路径
    """
    return os.path.join(get_user_home_dir(user_name), '.ssh')

def get_app_dir(user_name: str) -> str:
    """
    获取应用目录

    Args:
        user_name: 用户名

    Returns:
        str: 应用目录路径
    """
    return os.path.join(get_user_home_dir(user_name), 'nezha_app')

def get_dashboard_dir(user_name: str) -> str:
    """
    获取仪表盘目录

    Args:
        user_name: 用户名

    Returns:
        str: 仪表盘目录路径
    """
    return os.path.join(get_app_dir(user_name), 'dashboard')

def get_agent_dir(user_name: str) -> str:
    """
    获取代理目录

    Args:
        user_name: 用户名

    Returns:
        str: 代理目录路径
    """
    return os.path.join(get_app_dir(user_name), 'agent')

def get_ssh_ed25519_pri(user_name: str) -> str:
    """
    获取用户的ED25519私钥路径

    Args:
        user_name: 用户名

    Returns:
        str: ED25519私钥文件路径
    """
    ssh_dir = get_ssh_dir(user_name)
    return os.path.expanduser(os.path.join(ssh_dir, 'id_ed25519'))

def get_shell_run_cmd(shell_path: str, *args: Any) -> str:
    """
    构建shell命令字符串

    Args:
        shell_path: shell脚本路径
        *args: 命令参数

    Returns:
        str: 格式化后的shell命令
    """
    quoted_args = [shlex.quote(str(arg)) for arg in args]
    return f'{shell_path} {" ".join(quoted_args)}'

def run_shell_script(shell_path: str, *args: Any) -> bool:
    """
    运行shell脚本

    Args:
        shell_path: shell脚本路径
        *args: 脚本参数

    Returns:
        bool: 脚本是否成功执行
    """
    cmd = get_shell_run_cmd(shell_path, *args)
    result = os.system(cmd)

    if result == 0:
        logger.info(f"Shell命令执行成功: {cmd}")
        return True
    else:
        logger.error(f"Shell命令执行失败，退出代码 {result}: {cmd}")
        return False

def run_shell_command(command: str, shell: bool = True, capture_output: bool = False) -> Tuple[int, Optional[str], Optional[str]]:
    """
    运行shell命令并返回详细结果

    Args:
        command: 要执行的命令
        shell: 是否使用shell执行
        capture_output: 是否捕获输出

    Returns:
        Tuple[int, Optional[str], Optional[str]]: 退出代码、标准输出和标准错误
    """
    try:
        if capture_output:
            result = subprocess.run(
                command,
                shell=shell,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(command, shell=shell, check=False)
            return result.returncode, None, None
    except subprocess.SubprocessError as e:
        # 子进程执行错误
        logger.error(f"子进程执行错误: {command}, 错误: {str(e)}")
        return -1, None, f"子进程错误: {str(e)}"
    except FileNotFoundError as e:
        # 命令不存在
        logger.error(f"命令不存在: {command}, 错误: {str(e)}")
        return -2, None, f"命令不存在: {str(e)}"
    except PermissionError as e:
        # 权限错误
        logger.error(f"权限错误: {command}, 错误: {str(e)}")
        return -3, None, f"权限错误: {str(e)}"
    except Exception as e:
        # 其他未知错误
        logger.error(f"执行命令失败: {command}, 错误类型: {type(e).__name__}, 错误: {str(e)}")
        return -99, None, f"未知错误: {str(e)}"

def parse_heart_beat_extra_info(info: Optional[str]) -> Optional[dict]:
    """
    解析心跳额外信息

    Args:
        info: 心跳信息字符串

    Returns:
        Optional[dict]: 解析后的心跳信息字典，解析失败则返回None
    """
    if not info:
        return None

    parts = info.split('|')
    if len(parts) != 4:
        return None

    opt, hostname, port, username = parts
    return {
        "type": opt,
        "hostname": hostname,
        "port": int(port),
        "username": username
    }

def make_heart_beat_extra_info(info: Optional[dict], host_name: str, user_name: str) -> str:
    """
    生成心跳额外信息字符串

    Args:
        info: 心跳信息字典
        host_name: 主机名
        user_name: 用户名

    Returns:
        str: 格式化的心跳信息字符串
    """
    if not info:
        return f"0|{host_name}|22|{user_name}"

    return f"0|{info['hostname']}|{info['port']}|{info['username']}"

def need_check_and_heart_beat(heat_beat_extra_info: Optional[dict]) -> bool:
    """
    判断是否需要检查和心跳

    Args:
        heat_beat_extra_info: 心跳额外信息

    Returns:
        bool: 是否需要检查和心跳
    """
    # 自身定时任务执行
    if not heat_beat_extra_info:
        return True

    return heat_beat_extra_info.get('type') != "0"

def prompt_user_input(msg: str) -> bool:
    """
    提示用户输入并返回布尔结果

    Args:
        msg: 提示信息

    Returns:
        bool: 用户输入结果，Yes返回True，No返回False
    """
    valid_inputs = {'y', 'n'}

    while True:
        user_input = input(f"是否{msg}? (Y/y 是，N/n 否): ").strip().lower()

        if user_input in valid_inputs:
            return user_input == 'y'
        else:
            logger.info("无效输入，请输入 Y 或者 y 执行，N 或者 n 不执行")
