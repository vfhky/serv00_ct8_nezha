import sys
import argparse
from typing import Dict, Any

from cli.parser import create_parser
from cli.handler import CommandHandler

def main() -> int:
    """
    CLI主入口
    
    Returns:
        int: 退出码，0表示成功，非0表示失败
    """
    # 创建命令行参数解析器
    parser = create_parser()
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 如果没有提供命令，显示帮助信息
    if not args.command:
        parser.print_help()
        return 0
    
    # 将命名空间转换为字典
    args_dict = vars(args)
    
    # 创建命令处理器
    handler = CommandHandler(
        debug=args.debug,
        config_file=args.config
    )
    
    # 处理命令
    return handler.handle_command(args_dict)

if __name__ == "__main__":
    sys.exit(main())
