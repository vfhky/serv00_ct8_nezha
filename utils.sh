#!/bin/bash
# 通用工具脚本

init_vim() {
    cat <<EOF > ~/.vimrc
" 禁用鼠标模式
set mouse=
set number
set nopaste
EOF
}

alias_ll() {
    if [ ! -f ~/.profile ]; then
        touch ~/.profile
    fi
    if ! grep -q "alias ll='ls -lrhta'" ~/.profile; then
        echo "alias ll='ls -lrhta'" >> ~/.profile
    fi
}

add_x_to_script() {
    chmod +x *.sh
}

send_telegram_message() {
    if [ "$#" -ne 3 ]; then
        echo "Usage: $0 telegram chat_id token msg"
        exit 1
    fi

    local chat_id="$1"
    local bot_token="$2"
    local message="$3"
    local api_url="https://api.telegram.org/bot${bot_token}/sendMessage"

    curl -s -X POST "$api_url" -d chat_id="$chat_id" -d text="$message"
}

pushplus_notify() {
    if [ "$#" -ne 3 ]; then
        echo "Usage: $0 pushplus token title msg"
        exit 1
    fi

    local api_token="$1"
    local title="$2"
    local msg="$3"
    local api_url="http://www.pushplus.plus/send"

    local json_data
    json_data=$(cat <<EOF
{
    "token": "${api_token}",
    "title": "${title}",
    "content": "${msg}"
}
EOF
    )

    curl -X POST "$api_url" \
         -H "Content-Type: application/json" \
         -d "$json_data"
}

gen_ed25519() {
    local user_name=$(whoami)
    local ssh_dir="/home/${user_name}/.ssh"
    local pub_key="$ssh_dir/id_ed25519.pub"
    local private_key="$ssh_dir/id_ed25519"
    local authorized_keys="$ssh_dir/authorized_keys"

    if [ ! -d "$ssh_dir" ]; then
        mkdir -p "$ssh_dir"
        chmod 700 "$ssh_dir"
    fi

    if [ ! -f "$private_key" ]; then
        ssh-keygen -t ed25519 -C "vfhky@qq.com" -f "$private_key" -N ""
    fi

    if [ -f "$pub_key" ]; then
        cat "$pub_key" > "$authorized_keys"
    fi

    find "$ssh_dir" -type f -exec chmod 600 {} \;
    for file in "$pub_key" "$private_key" "$authorized_keys"; do
        if [ ! -f "$file" ]; then
            echo "Error: $file does not exist."
            exit 1
        fi
    done
}

rename_config_files() {
    local dir="$1"
    
    if [ ! -d "$dir" ]; then
        echo "目录 $dir 不存在"
        return 1
    fi

    for file in "$dir"/*.eg; do
        if [ -e "$file" ]; then
            local new_file="${file%.eg}.conf"
            
            if [ ! -e "$new_file" ]; then
                \cp -f "$file" "$new_file"
            fi
        fi
    done
}

modify_config() {
    user_name=$(whoami)
    nz_app_path="/home/${user_name}/nezha_app"
    script_dir=$(dirname "$(readlink -f "$0")")
    download_nezha_sh="${script_dir}/download_nezha.sh"
    heart_beat_entry_sh="${script_dir}/heart_beat_entry.sh"

    # 执行下载配置脚本
    "${download_nezha_sh}" config "${nz_app_path}"
    if [[ $? -ne 0 ]]; then
        echo "Error: 执行 ${download_nezha_sh} 失败."
    fi

    # 启动进程
    "${heart_beat_entry_sh}"
}

user_pkill() {
    user_name=$(whoami)
    echo "==> 停止用户 ${user_name} 所有应用"
    pkill -kill -u "${user_name}"
    echo "==> 停止用户 ${user_name} 完成"
}

restore() {
    user_pkill

    script_dir=$(dirname "$(readlink -f "$0")")
    find ~ -type f ! -path "$script_dir/*" -exec chmod 644 {} + 2>/dev/null
    find ~ -type d ! -path "$script_dir/*" -exec chmod 755 {} + 2>/dev/null
    find ~ ! -path "$script_dir/*" ! -path "$script_dir" -mindepth 1 -exec rm -rf {} + 2>/dev/null
}

init_all() {
    echo "===> 开始初始化所有配置"
    init_vim
    alias_ll
    add_x_to_script
    echo "===> 结束初始化所有配置"
}

gen_monitor_config() {
    if [ "$#" -ne 5 ]; then
        echo "Usage: $0 monitor 配置文件的完整路径  新增的进程路径  新增的进程名  进程的启动命令  新增的进程运行方式(background-前台 foreground-后台)"
        exit 1
    fi
    monitor_config=$1
    process_dir=$2
    process_name=$3
    process_run=$4
    process_run_mode=$5

    if [ ! -f "${monitor_config}" ]; then
        touch "${monitor_config}"
    fi

    config="${process_dir}|${process_name}|${process_run}|${process_run_mode}"
    if grep -q "${config}" "${monitor_config}"; then
        echo "监控配置 [${config}] 已经存在于 [${monitor_config}] 中，本次不予写入"
    else
        echo "${config}" >> "${monitor_config}"
    fi
}

gen_heart_beat_config() {
    if [ "$#" -ne 4 ]; then
        echo "Usage: $0 heart 配置文件的完整路径  serv00_ct8_host  serv00_ct8_port  serv00_ct8_username"
        exit 1
    fi
    heart_beat_config=$1
    serv00_ct8_host=$2
    serv00_ct8_port=$3
    serv00_ct8_username=$4

    if [ ! -f "${heart_beat_config}" ]; then
        touch "${heart_beat_config}"
    fi

    config="${serv00_ct8_host}|${serv00_ct8_port}|${serv00_ct8_username}"
    if grep -q "${config}" "${heart_beat_config}"; then
        echo "心跳配置 [${config}] 已经存在于 [${heart_beat_config}] 中，本次不予写入"
    else
        echo "${config}" >> "${heart_beat_config}"
    fi
}

add_cron_job() {
    if [ "$#" -lt 2 ]; then
        echo "Usage: $0 cron '定时时间' '脚本路径' [脚本参数...]"
        exit 1
    fi

    cron_time=$1
    script_path=$2
    shift 2
    script_params="$@"

    new_cron_job="$cron_time $script_path $script_params"
    existing_cron=$(crontab -l | grep -F "$script_path")

    if [ -n "$existing_cron" ]; then
        updated_cron=$(crontab -l | sed "s|^.*$script_path.*$|$new_cron_job|")
        echo "$updated_cron" | crontab -
        echo "定时任务已更新: $new_cron_job"
    else
        (crontab -l; echo "$new_cron_job") | crontab -
        echo "定时任务已添加: $new_cron_job"
    fi
}

update_check_cfg() {
    if [ "$#" -lt 2 ]; then
        echo "Usage: $0 <1-开启本机监控 | 0-关闭本机监控> <配置文件的完整路径>"
        exit 1
    fi

    opt=$1
    monitor_config_file=$2

    if [ ! -f "$monitor_config_file" ]; then
        echo "配置文件不存在: $monitor_config_file"
        exit 1
    fi

    if [ "$(uname)" = "FreeBSD" ]; then
        sed_command="sed -i ''"
    else
        sed_command="sed -i"
    fi

    if grep -q '^CHECK_MONITOR_URL_DNS=' "$monitor_config_file"; then
        eval "$sed_command 's/^CHECK_MONITOR_URL_DNS=.*/CHECK_MONITOR_URL_DNS=${opt}/' \"$monitor_config_file\""
        echo "更新了CHECK_MONITOR_URL_DNS=${opt}在配置文件中"
    else
        echo "CHECK_MONITOR_URL_DNS=${opt}" >> "$monitor_config_file"
        echo "追加了CHECK_MONITOR_URL_DNS=${opt}到配置文件中"
    fi
}


case "$1" in
    "init")
        init_all
        ;;
    "kill")
        user_pkill
        ;;
    "key")
        gen_ed25519
        ;;
    "monitor")
        shift 1
        gen_monitor_config "$@"
        ;;
    "heart")
        shift 1
        gen_heart_beat_config "$@"
        ;;
    "cron")
        shift 1
        add_cron_job "$@"
        ;;
    "check")
        shift 1
        update_check_cfg "$@"
        ;;
    "rename_config")
        shift 1
        rename_config_files "$@"
        ;;
    "modify_config")
        shift 1
        modify_config "$@"
        ;;
    "telegram")
        shift 1
        send_telegram_message "$@"
        ;;
    "pushplus")
        shift 1
        pushplus_notify "$@"
        ;;
    "restore")
        restore
        ;;
    *)
        echo "====== 用法 ====="
        echo "$0 init - 优化使用环境"
        echo "$0 kill - 停止用户所有应用"
        echo "$0 key - 生成 ed25519 公私钥"
        echo "$0 monitor - 写入进程监控配置, 参数: 配置文件的完整路径  新增的进程路径  新增的进程名 进程的启动命令 新增的进程运行方式(background-前台 foreground-后台)"
        echo "$0 heart - 写入心跳监控配置, 参数: 配置文件的完整路径  serv00_ct8_host  serv00_ct8_port  serv00_ct8_username"
        echo "$0 cron - 添加定时任务, 参数: '定时时间' '脚本路径' [脚本参数...]"
        echo "$0 check - [1-增加本机监控 0-关闭本机监控] 配置文件的完整路径"
        echo "$0 rename_config - 从配置模板文件中生成具体配置文件"
        echo "$0 modify_config - 修改哪吒dashboard或者agent的配置并重启服务"
        echo "$0 telegram - 发送telegram通知 chat_id token msg"
        echo "$0 pushplus - 发送pushplus通知 token title msg"
        echo "$0 restore - 重装系统"
        exit 1
        ;;
esac
