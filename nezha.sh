#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# 执行Python主程序
python3 "$SCRIPT_DIR/main.py" "$@"
