#!/bin/bash

if ! command -v pip &> /dev/null; then
    echo "pip could not be found. Please install pip and ensure it's in your PATH." >&2
    exit 1
fi

install_py_require() {
    local serv00_ct8_dir=$1

    local tmp_dir="${serv00_ct8_dir}/tmp"
    local requirements_file="${serv00_ct8_dir}/requirements.txt"
    local installed_modules_hash_file="${tmp_dir}/requirements_hash"

    mkdir -p "$tmp_dir"

    local current_hash=$(md5sum "$requirements_file" | awk '{print $1}')

    if [ ! -f "$installed_modules_hash_file" ] || [ "$(cat "$installed_modules_hash_file")" != "$current_hash" ]; then
        if pip install -r "$requirements_file"; then
            echo "$current_hash" > "$installed_modules_hash_file"
        else
            echo "Failed to install Python dependencies." >&2
            exit 1
        fi
    fi
}

check_process_running() {
    pgrep -f "$1" > /dev/null
}

# 设置环境变量
script_path=$(readlink -f "$0")
serv00_ct8_dir=$(dirname "$script_path")

# TYPE|USER|HOSTNAME|PORT
export HEART_BEAT_EXTRA_INFO="$1"

# 主逻辑脚本文件
heart_beat_logic_file="${serv00_ct8_dir}/heart_beat_logic.py"

processes=("heart_beat_")
for process in "${processes[@]}"; do
    if check_process_running "$process"; then
        exit 0
    fi
done

install_py_require "${serv00_ct8_dir}"

echo "即将执行 ${heart_beat_logic_file}"
python3 "${heart_beat_logic_file}"
