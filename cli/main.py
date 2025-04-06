import sys
import argparse
from typing import Dict, Any

from cli.parser import create_parser
from cli.handler import CommandHandler

def main() -> int:
    """CLI主入口"""
    # 创建命令行参数解析器
    parser = create_parser()

    # 解析命令行参数
    args = parser.parse_args()

    # 如果没有提供命令，显示帮助信息
    if not args.command:
        parser.print_help()
        return 0

    # 创建命令处理器
    handler = CommandHandler(
        debug=args.debug,
        config_file=args.config
    )

    # 处理命令
    return handler.handle_command(vars(args))

if __name__ == "__main__":
    sys.exit(main())
