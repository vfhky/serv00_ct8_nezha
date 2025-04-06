import argparse
from typing import List, Optional

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='哪吒探针安装和管理工具',
        formatter_class=argparse.RawTextHelpFormatter
    )

    # 添加全局参数
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--config', type=str, help='指定配置文件路径')

    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='命令')

    # 安装命令
    install_parser = subparsers.add_parser('install', help='安装服务')
    install_subparsers = install_parser.add_subparsers(dest='install_type', help='安装类型')

    # 安装Dashboard
    dashboard_parser = install_subparsers.add_parser('dashboard', help='安装哪吒面板')
    dashboard_parser.add_argument('--version', type=str, choices=['v0', 'v1'], default='v0', help='哪吒面板版本')
    dashboard_parser.add_argument('--http-port', type=int, default=8008, help='HTTP端口')
    dashboard_parser.add_argument('--grpc-port', type=int, default=5555, help='gRPC端口')
    dashboard_parser.add_argument('--grpc-host', type=str, default='0.0.0.0', help='gRPC监听地址')
    dashboard_parser.add_argument('--site-title', type=str, help='站点标题')
    dashboard_parser.add_argument('--admin', type=str, help='管理员用户名(GitHub用户名)')
    dashboard_parser.add_argument('--github-oauth-client-id', type=str, help='GitHub OAuth客户端ID')
    dashboard_parser.add_argument('--github-oauth-client-secret', type=str, help='GitHub OAuth客户端密钥')

    # 安装Agent
    agent_parser = install_subparsers.add_parser('agent', help='安装哪吒探针')
    agent_parser.add_argument('--version', type=str, choices=['v0', 'v1'], default='v0', help='哪吒探针版本')
    agent_parser.add_argument('--server', type=str, required=True, help='服务器地址，格式为 grpc.example.com:5555')
    agent_parser.add_argument('--key', type=str, required=True, help='Agent密钥')

    # 卸载命令
    uninstall_parser = subparsers.add_parser('uninstall', help='卸载服务')
    uninstall_subparsers = uninstall_parser.add_subparsers(dest='uninstall_type', help='卸载类型')

    # 卸载Dashboard
    uninstall_subparsers.add_parser('dashboard', help='卸载哪吒面板')

    # 卸载Agent
    uninstall_subparsers.add_parser('agent', help='卸载哪吒探针')

    # 启动命令
    start_parser = subparsers.add_parser('start', help='启动服务')
    start_subparsers = start_parser.add_subparsers(dest='start_type', help='启动类型')

    # 启动Dashboard
    start_subparsers.add_parser('dashboard', help='启动哪吒面板')

    # 启动Agent
    start_subparsers.add_parser('agent', help='启动哪吒探针')

    # 启动所有服务
    start_subparsers.add_parser('all', help='启动所有服务')

    # 停止命令
    stop_parser = subparsers.add_parser('stop', help='停止服务')
    stop_subparsers = stop_parser.add_subparsers(dest='stop_type', help='停止类型')

    # 停止Dashboard
    stop_subparsers.add_parser('dashboard', help='停止哪吒面板')

    # 停止Agent
    stop_subparsers.add_parser('agent', help='停止哪吒探针')

    # 停止所有服务
    stop_subparsers.add_parser('all', help='停止所有服务')

    # 重启命令
    restart_parser = subparsers.add_parser('restart', help='重启服务')
    restart_subparsers = restart_parser.add_subparsers(dest='restart_type', help='重启类型')

    # 重启Dashboard
    restart_subparsers.add_parser('dashboard', help='重启哪吒面板')

    # 重启Agent
    restart_subparsers.add_parser('agent', help='重启哪吒探针')

    # 重启所有服务
    restart_subparsers.add_parser('all', help='重启所有服务')

    # 状态命令
    status_parser = subparsers.add_parser('status', help='查看服务状态')
    status_subparsers = status_parser.add_subparsers(dest='status_type', help='状态类型')

    # 查看Dashboard状态
    status_subparsers.add_parser('dashboard', help='查看哪吒面板状态')

    # 查看Agent状态
    status_subparsers.add_parser('agent', help='查看哪吒探针状态')

    # 查看所有服务状态
    status_subparsers.add_parser('all', help='查看所有服务状态')

    # 备份命令
    backup_parser = subparsers.add_parser('backup', help='备份服务配置')
    backup_parser.add_argument('--target', type=str, help='备份目标路径')

    # 更新命令
    update_parser = subparsers.add_parser('update', help='更新服务')
    update_subparsers = update_parser.add_subparsers(dest='update_type', help='更新类型')

    # 更新Dashboard
    update_subparsers.add_parser('dashboard', help='更新哪吒面板')

    # 更新Agent
    update_subparsers.add_parser('agent', help='更新哪吒探针')

    # 更新全部
    update_subparsers.add_parser('all', help='更新所有服务')

    # 日志命令
    logs_parser = subparsers.add_parser('logs', help='查看服务日志')
    logs_subparsers = logs_parser.add_subparsers(dest='logs_type', help='日志类型')

    # 查看Dashboard日志
    dashboard_logs_parser = logs_subparsers.add_parser('dashboard', help='查看哪吒面板日志')
    dashboard_logs_parser.add_argument('--lines', type=int, default=100, help='显示行数')

    # 查看Agent日志
    agent_logs_parser = logs_subparsers.add_parser('agent', help='查看哪吒探针日志')
    agent_logs_parser.add_argument('--lines', type=int, default=100, help='显示行数')

    # 查看系统日志
    system_logs_parser = logs_subparsers.add_parser('system', help='查看系统日志')
    system_logs_parser.add_argument('--lines', type=int, default=100, help='显示行数')

    return parser
