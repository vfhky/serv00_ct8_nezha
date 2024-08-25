import paramiko
import os
from typing import Tuple, Dict, Any
from logger_wrapper import LoggerWrapper
from utils import get_shell_run_cmd

# 初始化日志记录器
logger = LoggerWrapper()

class ParamikoClient:
    def __init__(self, hostname: str, port: int = 22, username: str = None, password: str = None, 
                 ed25519_pri_file: str = None, timeout: int = 2, **kwargs):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.ed25519_pri_file = ed25519_pri_file
        self.timeout = timeout
        self.additional_options = kwargs
        self.client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self.client:
            self.client.close()
            logger.info(f"==> 关闭和 [{self.username}@{self.hostname}:{self.port}] 的SSH连接")
            self.client = None

    def _connect(self, connect_type: str, **kwargs) -> Tuple[int, str]:
        if not self.client:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_params = {
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username,
            'timeout': self.timeout,
            **self.additional_options,
            **kwargs  # 允许在调用时覆盖默认参数
        }

        try:
            if connect_type == 'password':
                connect_params['password'] = self.password
            else:
                pkey = paramiko.Ed25519Key(filename=self.ed25519_pri_file)
                connect_params['pkey'] = pkey

            self.client.connect(**connect_params)
            return 0, f"====> 连接成功 [{self.username}@{self.hostname}:{self.port}]"
        except paramiko.ssh_exception.AuthenticationException:
            return -1, f"====> 认证失败，请检查用户名和密码/密钥 [{self.username}@{self.hostname}:{self.port}]"
        except paramiko.ssh_exception.SSHException as ssh_error:
            return -2, f"====> SSH异常: {ssh_error} [{self.username}@{self.hostname}:{self.port}]"
        except FileNotFoundError as file_error:
            return -3, f"====> 密钥文件未找到: {file_error} [{self.username}@{self.hostname}:{self.port}]"
        except Exception as e:
            return -4, f"====> 连接失败，错误信息: {e} [{self.username}@{self.hostname}:{self.port}]"

    def password_connect(self, **kwargs) -> Tuple[int, str]:
        logger.info(f'==> 开始使用SSH密码连接主机 [{self.username}@{self.hostname}:{self.port}]')
        status, message = self._connect('password', **kwargs)
        if status == 0:
            logger.info(message)
        else:
            logger.error(message)
        return status, message

    def sshd_connect(self, **kwargs) -> Tuple[int, str]:
        logger.info(f'==> 开始使用SSH私钥连接主机 [{self.username}@{self.hostname}:{self.port}]')
        status, message = self._connect('key', **kwargs)
        if status == 0:
            logger.info(message)
        else:
            logger.error(message)
        return status, message

    def transfer_files(self, local_dir: str, remote_dir: str) -> None:
        if not self.client:
            logger.error(f"SSH client not connected [{self.username}@{self.hostname}:{self.port}]")
            return

        try:
            with self.client.open_sftp() as sftp:
                self.ensure_remote_dir_exists(sftp, remote_dir)
                logger.info(f"==> 开始拷贝[{local_dir}]目录到远程主机[{self.username}@{self.hostname}:{self.port}] [{remote_dir}]")
                
                for root, _, files in os.walk(local_dir):
                    for file in files:
                        local_file = os.path.join(root, file)
                        relative_path = os.path.relpath(local_file, local_dir)
                        remote_file = os.path.join(remote_dir, relative_path)

                        self.ensure_remote_dir_exists(sftp, os.path.dirname(remote_file))
                        sftp.put(local_file, remote_file, callback=lambda transferred, total: 
                                 logger.info(f"====> 传输进度[{self.username}@{self.hostname}:{self.port}] [{local_file}]: {transferred}/{total} bytes"))
                        local_mode = os.stat(local_file).st_mode
                        sftp.chmod(remote_file, local_mode)

                        logger.info(f"====> 拷贝文件 [{local_file}] 到远程成功[{self.username}@{self.hostname}:{self.port}]，权限设置为 {oct(local_mode)}")
        except Exception as e:
            logger.error(f"文件传输失败 {local_dir} ==> [{self.username}@{self.hostname}:{self.port}] : {e}")

    def ensure_remote_dir_exists(self, sftp, remote_dir: str) -> None:
        dirs = remote_dir.split('/')
        current_dir = ''
        for dir in dirs:
            if dir:
                current_dir = f"{current_dir}/{dir}"
                try:
                    sftp.stat(current_dir)
                except FileNotFoundError:
                    sftp.mkdir(current_dir)
                    logger.info(f"====> 创建远程目录 [{self.username}@{self.hostname}:{self.port}]: {current_dir}")

    def ssh_exec_script(self, script_file: str, *args: str) -> Tuple[int, str]:
        if not self.client:
            return -1, f"SSH client not connected [{self.username}@{self.hostname}:{self.port}]"
        
        try:
            cmd = get_shell_run_cmd(script_file, *args)
            logger.info(f"==> 执行远程命令 [{self.username}@{self.hostname}:{self.port}]: {cmd}")
            stdin, stdout, stderr = self.client.exec_command(cmd, timeout=self.timeout)
            exit_status = stdout.channel.recv_exit_status()

            stdout_output = stdout.read().decode()
            stderr_output = stderr.read().decode()

            logger.info(f"STDOUT: {stdout_output}\nSTDERR: {stderr_output}")

            if exit_status == 0:
                ret_msg = f'通过SSH执行 {cmd} 命令成功 [{self.username}@{self.hostname}:{self.port}]'
                logger.info(ret_msg)
                return 0, ret_msg
            else:
                ret_msg = f'通过SSH执行 {cmd} 命令时出错，退出状态码: {exit_status} [{self.username}@{self.hostname}:{self.port}]'
                logger.error(ret_msg)
                return -1, ret_msg
        except Exception as e:
            error_message = f"执行脚本失败 [{self.username}@{self.hostname}:{self.port}]: {str(e)}"
            logger.error(error_message)
            return -2, error_message
