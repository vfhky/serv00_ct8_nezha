#!/bin/bash

# 日志函数
log() {
    local level=$1
    shift
    case "$level" in
        "error") printf "\033[0;31m[错误] %s\033[0m\n" "$*" >&2 ;;
        "warn") printf "\033[0;33m[警告] %s\033[0m\n" "$*" ;;
        "info") printf "\033[0;32m[信息] %s\033[0m\n" "$*" ;;
        *) printf "%s\n" "$*" ;;
    esac
}

info() { log "info" "$@"; }
warn() { log "warn" "$@"; }
err() { log "error" "$@"; }

get_system_info() {
    local os_type=$(uname -s)
    local os_arch=$(uname -m)

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
    if [ "$(uname)" = "FreeBSD" ] || [ "$(uname)" = "Darwin" ]; then
        echo "sed -i ''"
    else
        echo "sed -i"
    fi
}

backup_config() {
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
        info "文件不存在，无需备份: $file_path"
        echo ""
    fi
}

get_latest_version() {
    local repo_pattern=$1
    shift

    for api in "$@"; do
        local version=$(curl -m 3 -sL "$api" | grep -E "tag_name|option\.value" | head -n 1 |
                 sed -E 's/.*"tag_name"[^"]*"([^"]+)".*/\1/; s/.*option\.value.*'"'"'([^'"'"']+)'"'"'.*/\1/; s/'$repo_pattern'/v/g; s/[\", ]//g')
        [ -n "$version" ] && { echo "$version"; return 0; }
    done

    return 1
}

configure_oauth() {
    local platform=$1
    local default_value=$2
    local platform_lower=$(echo "$platform" | tr '[:upper:]' '[:lower:]')
    local var_prefix="${platform_lower}"

    local enable_var="oauth2_${platform_lower}"
    prompt_input "是否开启 ${platform} 登录(y/n): " "$default_value" "$enable_var"

    if [[ "${!enable_var}" =~ ^[Yy]$ ]]; then
        prompt_input "请输入 ${platform} Client ID: " "" "${var_prefix}_client_id"
        prompt_input "请输入 ${platform} Client Secret: " "" "${var_prefix}_client_secret"
    fi
}

apply_oauth_config() {
    local platform=$1
    local config_file=$2
    local sed_command=$3
    local enable_var="oauth2_${platform}"

    local platform_upper="${platform^}"
    local client_id_var="${platform}_client_id"
    local client_secret_var="${platform}_client_secret"

    if [[ "${!enable_var}" =~ ^[Yy]$ ]]; then
        $sed_command "
            s/your_${platform}_client_id/${!client_id_var}/g;
            s/your_${platform}_client_secret/${!client_secret_var}/g;
        " "$config_file"
    fi
}

generate_dashboard_config() {
    info "> 修改面板配置"

    local config_dir=$1
    local need_backup=$2
    local config_file="${config_dir}/data/config.yaml"

    [ "$need_backup" = "1" ] && backup_config "$config_file" "dashboard配置"

    local temp_config="${config_dir}/nezha-config.yaml"
    cat > "${temp_config}" <<EOF
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
    prompt_input "===> 请输入面板访问端口: " "" nz_port
    prompt_input "===> 请输入面板设置的 GRPC 通信地址(如 $(whoami).serv00.net:${nz_port}): " "" nz_hostport
    prompt_input "===> 启用 SSL/TLS 加密(false-否 true-是，无特殊情况请选择false): " "false" nz_tls

    configure_oauth "GitHub" "y"
    configure_oauth "Gitee" "y"

    local sed_cmd=$(get_sed_cmd)

    $sed_cmd "
        s/nz_site_title/${nz_site_title}/g;
        s/nz_port/${nz_port}/g;
        s/nz_hostport/${nz_hostport}/g;
        s/nz_tls/${nz_tls}/g;
    " "$temp_config"

    apply_oauth_config "github" "$temp_config" "$sed_cmd"
    apply_oauth_config "gitee" "$temp_config" "$sed_cmd"

    mkdir -p "${config_dir}/data"
    mv -f "$temp_config" "$config_file"
    rm -f "${temp_config}.bak"

    info "===> 面板配置修改成功"
}

download_dashboard() {
    local install_path=$1

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

    mkdir -p "$install_path"
    local download_url="https://github.com/vfhky/nezha-build/releases/download/v${version}/nezha-dashboard.zip"

    if ! wget -qO "${install_path}/app.zip" "$download_url"; then
        err "===> [dashboard] ${download_url} 下载失败，请检查是否能正常访问"
        return 1
    fi

    info "===> [dashboard] ${download_url} 下载完成"

    local config_file="${install_path}/data/config.yaml"
    local config_backup=""
    if [ -f "$config_file" ]; then
        config_backup=$(backup_config "$config_file" "Dashboard配置")
    fi

    if ! unzip -oqq "${install_path}/app.zip" -d "$install_path"; then
        err "====> [dashboard] ${install_path}/app.zip 解压失败"
        return 1
    fi

    # 如果有备份的配置文件，恢复它
    if [ -n "$config_backup" ] && [ -f "$config_backup" ] && [[ ! "$modify_config" =~ ^[Yy]$ ]]; then
        info "正在恢复原配置文件..."
        mkdir -p "${install_path}/data"
        cp -f "$config_backup" "$config_file"
        info "配置文件已恢复"
    fi

    echo "v=${version}" > "${install_path}/version.txt"
    rm -f "${install_path}/app.zip"

    info "Dashboard 安装完成"
    info "版本: v${version}"
    info "安装路径: ${install_path}"
}

# 生成 Agent 配置
generate_agent_config() {
    local config_file=$1
    local need_backup=$2

    [ "$need_backup" = "1" ] && backup_config "$config_file" "Agent配置"

    cat > "$config_file" <<EOF
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

    prompt_input "===> 请输入面板密钥: " "" agent_secret
    prompt_input "===> 启用 SSL/TLS 加密(false-否 true-是): " "false" tls_enabled
    prompt_input "===> 请输入面板通信地址: " "" dashboard_addr
    local uuid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "$(date +%s%N)")

    local sed_cmd=$(get_sed_cmd)
    $sed_cmd "
        s/your_agent_secret/${agent_secret}/g;
        s/your_tls/${tls_enabled}/g;
        s/your_dashboard_ip_port/${dashboard_addr}/g;
        s/your_uuid/${uuid}/g;
    " "$config_file"

    rm -f "${config_file}.bak"
    info "Agent 配置生成成功: $config_file"
}

# 生成 Agent 运行脚本
generate_agent_script() {
    local agent_path=$1
    local config_file="${agent_path}/config.yml"

    if [ -f "$config_file" ]; then
        prompt_input "是否使用现有配置(y/n): " "y" use_existing
        if [[ ! "$use_existing" =~ ^[Yy]$ ]]; then
            generate_agent_config "$config_file" 1
        else
            info "使用现有 Agent 配置: $config_file"
        fi
    else
        generate_agent_config "$config_file" 0
    fi

    cat > "${agent_path}/nezha-agent.sh" <<EOF
#!/bin/bash
nohup ${agent_path}/nezha-agent \\
    -c ${config_file} \\
    > /dev/null 2>&1 &
EOF

    chmod +x "${agent_path}/nezha-agent.sh"
    info "Agent 启动脚本生成成功: ${agent_path}/nezha-agent.sh"
}

# 下载 Agent
download_agent() {
    local install_path=$1
    local sys_info
    local os_type
    local os_arch

    sys_info=$(get_system_info) || { err "获取系统信息失败"; exit 1; }
    IFS=':' read -r os_type os_arch <<< "$sys_info"
    info "系统类型: $os_type, 架构: $os_arch"

    version=$(get_latest_version "nezhahq/agent")
    if [ -z "$version" ]; then
        err "无法获取 Agent 版本"
        return 1
    fi

    info "最新版本: v${version}"

    # 确定下载URL
    local is_cn=$(check_location)
    local download_url
    if [ "$is_cn" = "true" ]; then
        info "检测到中国大陆网络环境，使用 Gitee 镜像"
        download_url="https://gitee.com/naibahq/agent/releases/download/v${version}/nezha-agent_${os_type}_${os_arch}.zip"
    else
        download_url="https://github.com/nezhahq/agent/releases/download/v${version}/nezha-agent_${os_type}_${os_arch}.zip"
    fi

    info "正在下载 Agent: $download_url"
    if ! wget -t 2 -T 60 -O "nezha-agent_${os_type}_${os_arch}.zip" "$download_url"; then
        err "从以下地址下载 Agent 失败: $download_url"
        return 1
    fi

    mkdir -p "$install_path"
    info "正在解压 Agent..."
    if ! unzip -qo "nezha-agent_${os_type}_${os_arch}.zip" && mv -f nezha-agent "$install_path"; then
        err "解压或移动 Agent 失败"
        return 1
    fi

    rm -f "nezha-agent_${os_type}_${os_arch}.zip"
    info "Agent 下载成功，版本: v${version}"
    info "安装路径: $install_path"

    generate_agent_script "$install_path"
}

# 修改配置
modify_config() {
    local app_path=$1
    info "开始准备修改，哪吒安装目录为: $app_path"

    prompt_input "修改 Dashboard 配置？(y/n): " "n" modify_dash
    if [[ "$modify_dash" =~ ^[Yy]$ ]]; then
        local dashboard_path="${app_path}/dashboard"
        local config_file="${dashboard_path}/data/config.yaml"

        if [ ! -f "$config_file" ]; then
            err "找不到 Dashboard 配置文件: $config_file"
            return 1
        fi

        generate_dashboard_config "$dashboard_path" 1

        # 重启 dashboard
        if pgrep -f nezha-dashboard >/dev/null; then
            info "正在重启 Dashboard..."
            pkill -f nezha-dashboard
            info "Dashboard 进程已终止，请手动重启"
        else
            info "未检测到运行中的 Dashboard 进程"
        fi
    fi

    prompt_input "修改 Agent 配置？(y/n): " "n" modify_agent
    if [[ "$modify_agent" =~ ^[Yy]$ ]]; then
        local agent_path="${app_path}/agent"
        local config_file="${agent_path}/config.yml"

        if [ ! -f "$config_file" ]; then
            err "找不到 Agent 配置文件: $config_file"
            return 1
        fi

        generate_agent_config "$config_file" 1

        # 重启 agent
        if pgrep -f nezha-agent >/dev/null; then
            info "正在重启 Agent..."
            pkill -f nezha-agent
            info "Agent 进程已终止，请手动重启"
        else
            info "未检测到运行中的 Agent 进程"
        fi
    fi

    info "配置修改完成"
}

# 显示帮助信息
show_help() {
    cat <<EOF
使用方法: $0 <命令> <路径>

命令:
  dashboard  下载并配置 Dashboard
  agent      下载并配置 Agent
  config     修改 Dashboard 或 Agent 的配置

示例:
  $0 dashboard /opt/nezha/dashboard  # 下载 Dashboard 到指定目录
  $0 agent /opt/nezha/agent          # 下载 Agent 到指定目录
  $0 config /opt/nezha               # 修改已安装的配置
EOF
}

# 主函数
main() {
    if [ "$#" -lt 2 ]; then
        show_help
        exit 1
    fi

    local command=$1
    local path=$2

    case "$command" in
        "dashboard")
            download_dashboard "$path"
            ;;
        "agent")
            download_agent "$path"
            ;;
        "config")
            modify_config "$path"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            err "无效的命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"