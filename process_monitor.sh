#!/bin/bash
# 用于管理进程

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 monitor.conf文件路径"
    exit 1
fi

config_file="$1"
if [ ! -f "$config_file" ]; then
    echo "配置文件 $config_file 不存在"
    exit 1
fi

declare -a process_list

while IFS='|' read -r app_path process_name script_command run_mode; do
    [[ "$app_path" =~ ^#.*$ ]] && continue
    process_list+=("$app_path|$process_name|$script_command|$run_mode")
done < "$config_file"

script_dir=$(dirname "$(realpath "$0")")

check_and_restart_processes() {
    for entry in "${process_list[@]}"; do
        IFS='|' read -ra process_info <<< "$entry"
        local app_path="${process_info[0]}"
        local process_name="${process_info[1]}"
        local cmd="${process_info[2]}"
        local run_mode="${process_info[3]}"

        if ! pgrep -x "$process_name" > /dev/null; then
            cd "$app_path" || continue

            if [[ "$run_mode" == "background" ]]; then
                echo "Process will run with nohup command: $cmd"
                nohup "$cmd" > /dev/null 2>&1 &
                echo "Process running with nohup command executed"
            else
                $cmd
            fi
            
            echo "[$app_path] Restarted process=[${cmd}] at $(date)" >> "${script_dir}/restart.log"
            cd "${script_dir}" || continue
            
            sleep 1
        else
            echo "Process '$process_name' is running."
        fi
    done
}

# 检查并重启进程
check_and_restart_processes
