#!/bin/bash

# 初始化安装路径
get_paths() {
    local root_path=${1%/}
    [ -z "$root_path" ] && { err "安装路径不能为空"; exit 1; }
    echo "${root_path}" "${root_path}/dashboard" "${root_path}/agent"
}

err() { printf "\033[31m%s\033[0m\n" "$*" >&2; }
info() { printf "\033[32m%s\033[0m\n" "$*"; }
warn() { printf "\033[33m%s\033[0m\n" "$*"; }

trap '[ -n "$TMP_FILES" ] && rm -f $TMP_FILES' EXIT

check_system() {
    os_type=$(uname -s)
    os_arch=$(uname -m)

    case "$os_type" in
        FreeBSD|Linux) ;;
        *) err "不支持的操作系统: $os_type"; exit 1 ;;
    esac

    case "$os_arch" in
        x86_64|amd64) os_arch="amd64" ;;
        i386|i686) os_arch="386" ;;
        aarch64|armv8b|armv8l) os_arch="arm64" ;;
        arm*) os_arch="arm" ;;
        s390x) os_arch="s390x" ;;
        riscv64) os_arch="riscv64" ;;
        *) err "不支持的架构: $os_arch"; exit 1 ;;
    esac
}

prompt_input() {
    local prompt_message=$1
    local default_value=$2
    local input_variable_name=$3

    while true; do
        printf "%s" "$prompt_message"
        read -r input_value

        if [ -n "$input_value" ]; then
            eval "$input_variable_name='$input_value'"
            break
        elif [ -n "$default_value" ]; then
            eval "$input_variable_name='$default_value'"
            break
        else
            warn "输入不能为空，请重新输入。"
        fi
    done
}

get_sed_cmd() {
    [ "$(uname)" = "FreeBSD" ] && echo "sed -i ''" || echo "sed -i";
}

backup_config_file() {
    local file_path=$1
    local file_type=${2:-"配置"}

    [ -z "$file_path" ] && { err "文件路径不能为空"; return 1; }

    if [ -f "$file_path" ]; then
        local backup_path="${file_path}.$(date +%Y_%m_%d_%H_%M)"
        if cp -f "$file_path" "$backup_path"; then
            info "====> 已备份${file_type}文件到 ${backup_path}"
            echo "$backup_path"
        else
            err "备份${file_type}文件失败"
            return 1
        fi
    else
        echo ""
    fi
}

get_latest_version() {
    local repo_pattern=$1
    shift

    for api in "$@"; do
        local version=$(curl -m 3 -sL "$api" | grep -E "tag_name|option\.value" | head -n 1 |
                 sed -E 's/.*"tag_name"[^"]*"([^"]+)".*/\1/; s/.*option\.value.*'"'"'([^'"'"']+)'"'"'.*/\1/; s/'$repo_pattern'/v/g; s/[", ]//g')
        [ -n "$version" ] && { echo "$version"; return 0; }
    done

    return 1
}

download_and_extract() {
    local download_url=$1
    local output_file=$2
    local extract_dir=$3
    local component=${4:-"组件"}

    [ -z "$download_url" ] && { err "下载URL不能为空"; return 1; }
    [ -z "$output_file" ] && { err "输出文件路径不能为空"; return 1; }
    [ -z "$extract_dir" ] && { err "解压目录不能为空"; return 1; }

    wget -t 2 -T 60 -qO "$output_file" "$download_url" || {
        err "[$component] [${download_url}] 下载失败，请检查网络连接";
        return 1;
    }

    info "===> [$component] [${download_url}] 下载完成"

    unzip -oqq "$output_file" -d "$extract_dir" || {
        err "[$component] [$output_file] 解压失败";
        return 1;
    }

    rm -f "$output_file"
    return 0
}

modify_dashboard_config() {
    local dashboard_path=$1
    local need_backup=$2
    info "> 修改面板配置"

    if [ "$need_backup" = "1" ]; then
        backup_config_file "${NZ_DASHBOARD_PATH}/data/config.yaml" "dashboard"
    fi

    local config_file="${NZ_DASHBOARD_PATH}/nezha-config.yaml"
    cat > "$config_file" <<EOF
debug: false
listenport: nz_port
language: zh_CN
sitename: "nz_site_title"
installhost: nz_hostport
tls: nz_tls
oauth2:
  GitHub:
    clientid: "your_github_client_id"
    clientsecret: "your_github_client_secret"
    endpoint:
      authurl: "https://github.com/login/oauth/authorize"
      tokenurl: "https://github.com/login/oauth/access_token"
    userinfourl: "https://api.github.com/user"
    useridpath: "id"
  Gitee:
    clientid: "your_gitee_client_id"
    clientsecret: "your_gitee_client_secret"
    endpoint:
      authurl: "https://gitee.com/oauth/authorize"
      tokenurl: "https://gitee.com/oauth/token"
    scopes:
      - user_info
    userinfourl: "https://gitee.com/api/v5/user"
    useridpath: "id"
EOF

    prompt_input "===> 请输入面板标题(如 TypeCodes Monitor): " "TypeCodes Monitor" nz_site_title
    prompt_input "===> 请输入面板访问端口(如 80): " "" nz_port
    prompt_input "===> 请输入面板设置的 GRPC 通信地址(如 $(whoami).serv00.net:${nz_port}): " "" nz_hostport
    prompt_input "===> 启用针对 gRPC 端口的 SSL/TLS加密，无特殊情况请选择false-否 true-是: " "false" nz_tls

    local sed_cmd=$(get_sed_cmd)
    $sed_cmd "s/nz_site_title/${nz_site_title}/; s/nz_port/${nz_port}/; s/nz_hostport/${nz_hostport}/; s/nz_tls/${nz_tls}/" "$config_file"

    prompt_input "===> 是否开启 GitHub 登录(y-是 n-否): " "y" oauth2_github
    if [[ "${oauth2_github}" =~ ^[Yy]$ ]]; then
        prompt_input "===> 请输入 Github Client ID: " "" github_client_id
        prompt_input "===> 请输入 Github Client Secret: " "" github_client_secret
        $sed_cmd "s/your_github_client_id/${github_client_id}/; s/your_github_client_secret/${github_client_secret}/" "$config_file"
    fi

    prompt_input "===> 是否开启 Gitee 登录(y-是 n-否): " "y" oauth2_gitee
    if [[ "${oauth2_gitee}" =~ ^[Yy]$ ]]; then
        prompt_input "===> 请输入 Gitee Client ID: " "" gitee_client_id
        prompt_input "===> 请输入 Gitee Client Secret: " "" gitee_client_secret
        $sed_cmd "s/your_gitee_client_id/${gitee_client_id}/; s/your_gitee_client_secret/${gitee_client_secret}/" "$config_file"
    fi

    mkdir -p "$dashboard_path/data"
    mv -f "$config_file" "${dashboard_path}/data/config.yaml"
    info "===> 面板配置修改成功"
}

download_dashboard() {
    check_system

    local paths=($(get_paths "$1"))
    local root_path=${paths[0]}
    local dashboard_path=${paths[1]}

    mkdir -p "$dashboard_path"

    # 获取最新版本
    local api_list=(
        "https://api.github.com/repos/vfhky/nezha-build/releases/latest"
        "https://ghapi.1024.cloudns.org?pj=vfhky/nezha-build"
        "https://fastly.jsdelivr.net/gh/vfhky/nezha-build/"
        "https://gcore.jsdelivr.net/gh/vfhky/nezha-build/"
    )

    local version=$(get_latest_version "vfhky\/nezha-build@" "${api_list[@]}")

    if [ -z "$version" ]; then
        err "获取 Dashboard 版本号失败，请检查本机能否连接 ${array[0]}"
        return 1
    fi

    info "当前最新版本为: $version"
    local version_num=${version#v}

    if ! download_and_extract "https://github.com/vfhky/nezha-build/releases/download/${version}/nezha-dashboard.zip" \
                            "${dashboard_path}/app.zip" \
                            "$dashboard_path" \
                            "dashboard"; then
        exit 1
    fi

    local config_file="${dashboard_path}/data/config.yaml"
    handle_config_file "$config_file" "dashboard" "modify_dashboard_config $dashboard_path"

    echo "v=${version_num}" > "${dashboard_path}/version.txt"
    info "===> Dashboard 安装完成，版本: ${version}"
}

gen_agent_config() {
    local agent_config_file="$1"
    local need_backup=$2
    local agent_path=$3

    [ -z "$agent_config_file" ] && { echo "File path is required."; return 1; }

    if [ "$need_backup" = "1" ]; then
        backup_config_file "$agent_config_file" "agent"
    fi

    cat > "$agent_config_file" <<EOF
client_secret: your_agent_secret
debug: false
disable_auto_update: false
disable_command_execute: false
disable_force_update: false
disable_nat: false
disable_send_query: false
gpu: false
insecure_tls: your_tls
ip_report_period: 1800
report_delay: 1
server: your_dashboard_ip_port
skip_connection_count: false
skip_procs_count: false
temperature: false
tls: your_tls
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: your_uuid
EOF

    prompt_input "===> 请输入面板配置文件中的密钥agentsecretkey: " "" your_agent_secret
    prompt_input "===> 启用针对 gRPC 端口的 SSL/TLS加密，无特殊情况请选择false-否 true-是: " "false" your_tls
    prompt_input "===> 请输入面板设置的 GRPC 通信地址(例如 vfhky.serv00.net:8888): " "" your_dashboard_ip_port
    your_uuid=$(uuidgen)

    local sed_cmd=$(get_sed_cmd)
    $sed_cmd "s/your_agent_secret/${your_agent_secret}/; s/your_tls/${your_tls}/g; s/your_dashboard_ip_port/${your_dashboard_ip_port}/; s/your_uuid/${your_uuid}/" "$agent_config_file"
}

handle_config_file() {
    local config_file=$1
    local component=$2
    local config_func_cmd=$3

    if [ -f "$config_file" ]; then
        local backup_file=$(backup_config_file "$config_file" "$component")

        prompt_input "===> 是否继续使用旧的配置数据(Y/y 是，N/n 否): " "" modify
        if [[ "${modify}" =~ ^[Yy]$ ]]; then
            [ -n "$backup_file" ] && mv -f "$backup_file" "$config_file"
            info "===> [$component] 已使用旧配置"
            return 0
        fi
    fi

    info "===> [$component] 准备输入新配置"
    eval $config_func_cmd 0
    return 1
}

download_agent() {
    check_system

    local paths=($(get_paths "$1"))
    local root_path=${paths[0]}
    local agent_path=${paths[2]}

    mkdir -p "$agent_path"

    local api_list=(
        "https://api.github.com/repos/nezhahq/agent/releases/latest"
        "https://gitee.com/api/v5/repos/naibahq/agent/releases/latest"
        "https://fastly.jsdelivr.net/gh/nezhahq/agent/"
        "https://gcore.jsdelivr.net/gh/nezhahq/agent/"
    )

    local version=$(get_latest_version "nezhahq\/agent@" "${api_list[@]}")

    if [ -z "$version" ]; then
        err "获取 Agent 版本号失败，请检查网络连接"
        return 1
    fi

    info "当前最新版本为: ${version}"

    # 下载并解压
    local download_url="https://github.com/nezhahq/agent/releases/download/${version}/nezha-agent_${os_type}_${os_arch}.zip"
    local output_file="nezha-agent_${os_type}_${os_arch}.zip"

    if ! wget -t 2 -T 60 -O "$output_file" "$download_url"; then
        err "Agent 下载失败，请检查网络连接 ${api_list[0]}"
        return 1
    fi

    info "===> Agent 下载完成"

    if ! unzip -qo "$output_file"; then
        err "Agent 解压失败"
        return 1
    fi

    mv -f nezha-agent "$agent_path"
    rm -f "$output_file"

    gen_agent_run_sh "$agent_path"
}

gen_agent_run_sh() {
    local agent_path=$1
    local agent_run_sh="${agent_path}/nezha-agent.sh"
    local config_file="${agent_path}/config.yml"

    if [ -f "$config_file" ]; then
        prompt_input "===> 是否继续使用旧的配置数据(Y/y 是，N/n 否): " "" modify
        if [[ "${modify}" =~ ^[Yy]$ ]]; then
            info "===> [agent] 您选择继续使用旧的配置文件[$config_file]"
            return 0
        else
            info "===> [agent] 准备输入新的配置数据"
            gen_agent_config "$config_file" 1 "$agent_path"
        fi
    else
        info "===> [agent] 准备输入新的配置数据"
        gen_agent_config "$config_file" 0 "$agent_path"
    fi

    cat > "$agent_run_sh" <<EOF
#!/bin/bash
nohup ${agent_path}/nezha-agent \\
    -c ${config_file} \\
    > /dev/null 2>&1 &
EOF

    chmod +x "$agent_run_sh"
}

# 修改现有配置
modify_config() {
    info "====> 开始准备修改，已知哪吒安装目录为[$1]"
    check_system

    local paths=($(get_paths "$1"))
    local root_path=${paths[0]}
    local dashboard_path=${paths[1]}
    local agent_path=${paths[2]}

    prompt_input "===> 是否修改dashboard配置(Y/y 是，N/n 否): " "N" modify
    if [[ "${modify}" =~ ^[Yy]$ ]]; then
        local dashboard_config_file="${dashboard_path}/data/config.yaml"
        if [ ! -f "$dashboard_config_file" ]; then
            err "dashboard的配置文件[$dashboard_config_file]不存在，请检查是否已经安装"
            exit 1
        fi

        info "====> 准备开始修改dashboard配置文件[$dashboard_config_file]"
        modify_dashboard_config "$dashboard_path" 1

        if dashboard_pid=$(pgrep -f nezha-dashboard); then
            kill -9 "$dashboard_pid"
            info "====> 关闭哪吒dashboard进程成功"
        fi
    fi

    prompt_input "===> 是否修改agent配置(Y/y 是，N/n 否): " "N" modify
    if [[ "${modify}" =~ ^[Yy]$ ]]; then
        agent_config_file="${agent_path}/config.yml"
        if [ ! -f "$agent_config_file" ]; then
            err "agent的配置文件[$agent_config_file]不存在，请检查是否已经安装"
            exit 1
        fi

        info "====> 准备开始修改agent配置文件[$agent_config_file]"
        gen_agent_config "$agent_config_file" 1 "$agent_path"

        if agent_pid=$(pgrep -f nezha-agent); then
            kill -9 "$agent_pid"
            info "====> 关闭哪吒agent进程成功"
        fi
    fi
}


if [ "$#" -lt 2 ]; then
    echo "Error: Not enough arguments provided."
    echo "Usage: $0 <command> <arg>"
    echo "Commands:"
    echo "  dashboard  app 下载 dashboard"
    echo "  agent       下载 agent"
    echo "  config      修改dashboard或者agent的配置"
    exit 1
fi

command="$1"
arg="$2"

case "$command" in
    "dashboard")
        download_dashboard "$arg"
        ;;
    "agent")
        download_agent "$arg"
        ;;
    "config")
        modify_config "$arg"
        ;;
    *)
        echo "Error: Invalid command '$command'"
        echo "====== Usage ======"
        echo "  $0 dashboard <arg>   下载 dashboard"
        echo "  $0 agent <arg>       下载 agent"
        echo "  $0 config <arg>      修改dashboard或者agent的配置"
        exit 1
        ;;
esac

