#!/bin/bash

if ! command -v pip &> /dev/null; then
    echo "pip could not be found. Please install pip and ensure it's in your PATH." >&2
    exit 1
fi

install_py_require() {
    local serv00_ct8_dir=$1

    # 检查pip是否存在
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        echo "错误: pip 或 pip3 命令不存在，请先安装Python pip工具" >&2
        return 1
    fi

    local pip_cmd="pip"
    if ! command -v pip &> /dev/null && command -v pip3 &> /dev/null; then
        pip_cmd="pip3"
    fi

    local tmp_dir="${serv00_ct8_dir}/tmp"
    local requirements_file="${serv00_ct8_dir}/requirements.txt"
    local installed_modules_hash_file="${tmp_dir}/requirements_hash"

    # 确保tmp目录存在
    mkdir -p "$tmp_dir"

    # 如果requirements.txt不存在，则报错并退出
    if [ ! -f "$requirements_file" ]; then
        echo "错误: requirements.txt文件不存在: $requirements_file" >&2
        return 1
    fi

    local current_hash=$(md5sum "$requirements_file" 2>/dev/null || md5 -q "$requirements_file" 2>/dev/null)
    if [ -z "$current_hash" ]; then
        echo "警告: 无法计算requirements.txt的哈希值，将尝试安装全部依赖" >&2
        current_hash="force_install_$(date +%s)"
    fi

    if [ ! -f "$installed_modules_hash_file" ] || [ "$(cat "$installed_modules_hash_file")" != "$current_hash" ]; then
        echo "安装Python依赖..." >&2
        if $pip_cmd install -r "$requirements_file"; then
            echo "$current_hash" > "$installed_modules_hash_file"
            echo "Python依赖安装成功" >&2
        else
            echo "错误: Python依赖安装失败" >&2
            return 1
        fi
    else
        echo "Python依赖已经安装，跳过安装步骤" >&2
    fi

    return 0
}

count_processes() {
    pgrep -f "$1" | wc -l
}

# 设置环境变量
script_path=$(readlink -f "$0")
serv00_ct8_dir=$(dirname "$script_path")

# TYPE|USER|HOSTNAME|PORT
export HEART_BEAT_EXTRA_INFO="$1"

# 主逻辑脚本文件
heart_beat_logic_file="${serv00_ct8_dir}/heart_beat_logic.py"

process_count=$(count_processes "heart_beat_")
if [ "$process_count" -gt 1 ]; then
    exit 0
fi

install_py_require "${serv00_ct8_dir}"

echo "即将执行 ${heart_beat_logic_file}"
python3 "${heart_beat_logic_file}"
