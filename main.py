#!/usr/bin/env python3
import sys
import os
import logging

# 添加当前目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入CLI主入口
from cli.main import main

if __name__ == "__main__":
    # 设置执行权限
    os.chmod(__file__, 0o755)
    
    # 运行CLI
    sys.exit(main())
