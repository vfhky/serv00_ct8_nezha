#!/bin/bash


err() {
    printf "${red}$*${plain}\n" >&2
}

install_base() {
    (command -v curl >/dev/null 2>&1 && command -v wget >/dev/null 2>&1 && command -v unzip >/dev/null 2>&1) ||
        (install_soft curl wget unzip)
}

install_soft() {
    (command -v yum >/dev/null 2>&1 && yum makecache && yum install $* selinux-policy -y) ||
        (command -v apt >/dev/null 2>&1 && apt update && apt install $* selinux-utils -y) ||
        (command -v pacman >/dev/null 2>&1 && pacman -Syu $* base-devel --noconfirm && install_arch) ||
        (command -v apt-get >/dev/null 2>&1 && apt-get update && apt-get install $* selinux-utils -y) ||
        (command -v apk >/dev/null 2>&1 && apk update && apk add $* -f)
}

geo_check() {
    api_list="https://blog.cloudflare.com/cdn-cgi/trace https://dash.cloudflare.com/cdn-cgi/trace https://cf-ns.com/cdn-cgi/trace"
    ua="Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0"
    set -- $api_list
    for url in $api_list; do
        text="$(curl -A $ua -m 10 -s $url)"
        if echo $text | grep -qw 'CN'; then
            isCN=true
            break
        fi
    done
}

pre_check() {
    os_type=$(uname -s)
    os_arch=$(uname -m)

    case "$os_type" in
        FreeBSD|Linux)
            ;;
        *)
            echo "Unsupported operating system: $os_type"
            exit 1
            ;;
    esac

    case "$os_arch" in
        x86_64|amd64)
            os_arch="amd64"
            ;;
        i386|i686)
            os_arch="386"
            ;;
        aarch64|armv8b|armv8l)
            os_arch="arm64"
            ;;
        arm*)
            os_arch="arm"
            ;;
        s390x)
            os_arch="s390x"
            ;;
        riscv64)
            os_arch="riscv64"
            ;;
        *)
            echo "Unsupported architecture: $os_arch"
            exit 1
            ;;
    esac

    ## China_IP
    if [ -z "$CN" ]; then
        geo_check
        if [ ! -z "$isCN" ]; then
            echo "根据geoip api提供的信息，当前IP可能在中国"
            printf "是否选用中国镜像完成安装? [Y/n] (自定义镜像输入 3):"
            read -r input
            case $input in
            [yY][eE][sS] | [yY])
                echo "使用中国镜像"
                CN=true
                ;;

            [nN][oO] | [nN])
                echo "不使用中国镜像"
                ;;

            [3])
                echo "使用自定义镜像"
                printf "请输入自定义镜像 (例如:dn-dao-github-mirror.daocloud.io),留空为不使用: "
                read -r input
                case $input in
                *)
                    CUSTOM_MIRROR=$input
                    ;;
                esac

                ;;
            *)
                echo "使用中国镜像"
                CN=true
                ;;
            esac
        fi
    fi

    if [ -n "$CUSTOM_MIRROR" ]; then
        GITHUB_RAW_URL="gitee.com/naibahq/scripts/raw/main"
        GITHUB_URL=$CUSTOM_MIRROR
        Docker_IMG="registry.cn-shanghai.aliyuncs.com\/naibahq\/nezha-dashboard"
    else
        if [ -z "$CN" ]; then
            GITHUB_RAW_URL="raw.githubusercontent.com/nezhahq/scripts/main"
            GITHUB_URL="github.com"
            Docker_IMG="ghcr.io\/nezhahq\/nezha"
        else
            GITHUB_RAW_URL="gitee.com/naibahq/scripts/raw/main"
            GITHUB_URL="gitee.com"
            Docker_IMG="registry.cn-shanghai.aliyuncs.com\/naibahq\/nezha-dashboard"
        fi
    fi
}

# Function to prompt and read input with validation
prompt_input() {
    local prompt_message=$1
    local default_value=$2
    local input_variable_name=$3

    while true; do
        printf "%s" "$prompt_message"
        read -r input_value
        if [ -z "$input_value" ] && [ -n "$default_value" ]; then
            eval "$input_variable_name='$default_value'"
            break
        elif [ -n "$input_value" ]; then
            eval "$input_variable_name='$input_value'"
            break
        else
            echo "输入不能为空，请重新输入。"
        fi
    done
}

modify_dashboard_config() {
    echo "> 修改面板配置"

    local config_file="${NZ_DASHBOARD_PATH}/nezha-config.yaml"
    if [ "$IS_DOCKER_NEZHA" = 1 ]; then
        echo "正在下载 Docker 脚本"
        wget -t 2 -T 60 -O /tmp/nezha-docker-compose.yaml https://${GITHUB_RAW_URL}/script/docker-compose.yaml >/dev/null 2>&1
        if [ $? != 0 ]; then
            err "下载脚本失败，请检查本机能否连接 ${GITHUB_RAW_URL}"
            return 0
        fi
    fi

    wget -t 2 -T 60 -O "${config_file}" https://${GITHUB_RAW_URL}/extras/config.yaml >/dev/null 2>&1
    if [ $? != 0 ]; then
        err "下载脚本失败，请检查本机能否连接 https://${GITHUB_RAW_URL}/extras/config.yaml"
        return 0
    fi

    prompt_input "===> 请输入面板标题(如 TypeCodes Monitor): " "TypeCodes Monitor" nz_site_title
    prompt_input "===> 请输入面板访问端口(如 80):  " "" nz_port
    prompt_input "===> 请输入面板设置的 GRPC 通信地址(例如 vfhky.serv00.net:8888)  " "" nz_hostport
    prompt_input "===> 启用针对 gRPC 端口的 SSL/TLS加密，无特殊情况请选择false-否 true-是: " "false" nz_tls

    #sed -i "s/nz_site_title/${nz_site_title}/" "${config_file}"
    sed -i '' "s/nz_site_title/${nz_site_title}/" "${config_file}"

    #sed -i "s/nz_port/${nz_port}/" "${config_file}"
    sed -i '' "s/nz_port/${nz_port}/" "${config_file}"

    #sed -i "s/nz_hostport/${nz_hostport}/" "${config_file}"
    sed -i '' "s/nz_hostport/${nz_hostport}/" "${config_file}"

    #sed -i "s/nz_tls/${nz_tls}/" "${config_file}"
    sed -i '' "s/nz_tls/${nz_tls}/" "${config_file}"

    #sed -i "s/nz_language/zh_CN/" "${config_file}"
    sed -i '' "s/nz_language/zh_CN/" "${config_file}"

    mkdir -p $NZ_DASHBOARD_PATH/data  2>/dev/null 
    \mv -f "${config_file}" ${NZ_DASHBOARD_PATH}/data/config.yaml
    if [ "$IS_DOCKER_NEZHA" = 1 ]; then
        mv -f /tmp/nezha-docker-compose.yaml ${NZ_DASHBOARD_PATH}/docker-compose.yaml
    fi

    printf "===> 面板配置 ${green}修改成功 ${plain}\n"
}

download_dashboard() {
    pre_check
    install_base

    NZ_DASHBOARD_PATH=$1
    mkdir -p "${NZ_DASHBOARD_PATH}"

    local version=$(curl -m 3 -sL "https://api.github.com/repos/vfhky/nezha-build/releases/latest" | grep "tag_name" | head -n 1 | awk -F ":" '{print $2}' | sed 's/\"//g;s/,//g;s/ //g')
    if [ -z "${version}" ]; then
        version=$(curl -m 3 -sL "github-api.vfhky.workers.dev?pj=vfhky/nezha-build" | grep "tag_name" | head -n 1 | awk -F ":" '{print $2}' | sed 's/\"//g;s/,//g;s/ //g')
    fi
    if [ -z "${version}" ]; then
        version=$(curl -m 3 -sL "https://fastly.jsdelivr.net/gh/vfhky/nezha-build/" | grep "option\.value" | awk -F "'" '{print $2}' | sed 's/vfhky\/nezha-build@/v/g')
    fi
    if [ -z "${version}" ]; then
        version=$(curl -m 3 -sL "https://gcore.jsdelivr.net/gh/vfhky/nezha-build/" | grep "option\.value" | awk -F "'" '{print $2}' | sed 's/vfhky\/nezha-build@/v/g')
    fi

    if [ -z "$version" ]; then
        err "获取 Dashboard 版本号失败，请检查本机能否链接 https://api.github.com/repos/vfhky/nezha-build/releases/latest"
        return 1
    fi

    local version_num=$(echo "$version" | sed 's/^v//')
    echo "当前最新版本为: v${version_num}"

    NZ_DASHBOARD_URL="https://github.com/vfhky/nezha-build/releases/download/${version}/nezha-dashboard.zip"
    #if [ -z "$CN" ]; then
    #    NZ_DASHBOARD_URL="https://${GITHUB_URL}/naiba/nezha/archive/refs/tags/$version.zip"
    #else
    #    NZ_DASHBOARD_URL="https://${GITHUB_URL}/naibahq/nezha/archive/refs/tags/$version.zip"
    #fi

    wget -qO "${NZ_DASHBOARD_PATH}"/app.zip $NZ_DASHBOARD_URL >/dev/null 2>&1
    if [ ! -f "${NZ_DASHBOARD_PATH}"/app.zip ]; then
        echo "===> [dashboard] ${NZ_DASHBOARD_URL} 下载失败，请检查是否能正常访问"
        exit 1
    fi

    echo "===> [dashboard] ${NZ_DASHBOARD_URL} 下载完成"

    local config_file="${NZ_DASHBOARD_PATH}/data/config.yaml"
    local config_file_bak=''
    if [[ -f "${config_file}" ]]; then
        local config_file_bak="${config_file}.$(date +%Y_%m_%d_%H_%M)"
        \cp -f "${config_file}" "${config_file_bak}"
        echo "====> 已经备份dashboard的配置文件[${config_file}] 到 ${config_file_bak}"
    fi

    version_file="${NZ_DASHBOARD_PATH}/version.txt"
    if ! unzip -oqq "${NZ_DASHBOARD_PATH}"/app.zip -d "${NZ_DASHBOARD_PATH}"; then
        echo "====> [dashboard] ${NZ_DASHBOARD_PATH}/app.zip 解压失败"
        exit 1
    fi

    echo "v=${version_num}" > "${version_file}"
    \rm -rf "${NZ_DASHBOARD_PATH}"/app.zip

    if [[ -f "${config_file_bak}" ]]; then
        prompt_input "===> 是否继续使用旧的配置数据(Y/y 是，N/n 否): " "" modify
        if [[ "${modify}" =~ ^[Yy]$ ]]; then
            mv -f "${config_file_bak}" "${config_file}"
            echo "===> [dashboard] 已经成功使用旧的配置数据 ${config_file}"
        else
            echo "===> [dashboard] 准备输入新的配置数据"
            modify_dashboard_config
        fi
    else
        echo "===> [dashboard] 准备输入新的配置数据"
        modify_dashboard_config
    fi
}

download_agent() {
    pre_check
    install_base

    NZ_AGENT_PATH=$1

    echo "正在获取监控Agent版本号"

    local version=$(curl -m 10 -sL "https://api.github.com/repos/nezhahq/agent/releases/latest" | grep "tag_name" | head -n 1 | awk -F ":" '{print $2}' | sed 's/\"//g;s/,//g;s/ //g')
    if [ ! -n "$version" ]; then
        version=$(curl -m 10 -sL "https://gitee.com/api/v5/repos/naibahq/agent/releases/latest" | awk -F '"' '{for(i=1;i<=NF;i++){if($i=="tag_name"){print $(i+2)}}}')
    fi
    if [ ! -n "$version" ]; then
        version=$(curl -m 10 -sL "https://fastly.jsdelivr.net/gh/nezhahq/agent/" | grep "option\.value" | awk -F "'" '{print $2}' | sed 's/nezhahq\/agent@/v/g')
    fi
    if [ ! -n "$version" ]; then
        version=$(curl -m 10 -sL "https://gcore.jsdelivr.net/gh/nezhahq/agent/" | grep "option\.value" | awk -F "'" '{print $2}' | sed 's/nezhahq\/agent@/v/g')
    fi

    if [ ! -n "$version" ]; then
        err "获取版本号失败，请检查本机能否链接 https://api.github.com/repos/nezhahq/agent/releases/latest"
        return 1
    else
        echo "当前最新版本为: ${version}"
    fi

    echo "正在下载Agent...."
    if [ -z "$CN" ]; then
        NZ_AGENT_URL="https://${GITHUB_URL}/nezhahq/agent/releases/download/${version}/nezha-agent_${os_type}_${os_arch}.zip"
    else
        NZ_AGENT_URL="https://${GITHUB_URL}/naibahq/agent/releases/download/${version}/nezha-agent_${os_type}_${os_arch}.zip"
    fi
    wget -t 2 -T 60 -O nezha-agent_linux_${os_arch}.zip $NZ_AGENT_URL >/dev/null 2>&1
    if [ $? != 0 ]; then
        err "Release 下载失败，请检查本机能否连接 ${GITHUB_URL}"
        return 1
    fi

    mkdir -p $NZ_AGENT_PATH  2>/dev/null
    unzip -qo nezha-agent_linux_${os_arch}.zip &&
        \mv -f nezha-agent $NZ_AGENT_PATH &&
        rm -rf nezha-agent_linux_${os_arch}.zip README.md

    echo "===> Agent ${NZ_AGENT_URL} 下载完成"

    gen_agent_run_sh
}

gen_agent_config() {
  local file_path="$1"

  if [ -z "$file_path" ]; then
    echo "File path is required."
    return 1
  fi

  \rm -rf "$file_path"

  cat > "$file_path" <<EOF
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
tls: false
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: your_uuid
EOF

prompt_input "===> 请输入面板配置文件中的密钥agentsecretkey: " "" your_agent_secret
prompt_input "===> 启用针对 gRPC 端口的 SSL/TLS加密，无特殊情况请选择false-否 true-是: " "false" your_tls
prompt_input "===> 请输入面板设置的 GRPC 通信地址(例如 vfhky.serv00.net:8888):  " "" your_dashboard_ip_port
your_uuid=$(uuidgen)

#sed -i "s/your_agent_secret/${your_agent_secret}/" "$file_path"
sed -i '' "s/your_agent_secret/${your_agent_secret}/" "$file_path"

#sed -i "s/your_tls/${your_tls}/" "$file_path"
sed -i '' "s/your_tls/${your_tls}/" "$file_path"

#sed -i "s/your_dashboard_ip_port/${your_dashboard_ip_port}/" "$file_path"
sed -i '' "s/your_dashboard_ip_port/${your_dashboard_ip_port}/" "$file_path"

#sed -i "s/your_uuid/${your_uuid}/" "$file_path"
sed -i '' "s/your_uuid/${your_uuid}/" "$file_path"
}

gen_agent_run_sh() {
    local agent_run_sh="${NZ_AGENT_PATH}/nezha-agent.sh"
    local config_file="${NZ_AGENT_PATH}/config.yml"
    local config_file_bak=""

    if [[ -f "${config_file}" ]]; then
        config_file_bak="${config_file}.$(date +%Y_%m_%d_%H_%M)"
        prompt_input "===> 是否继续使用旧的配置数据(Y/y 是，N/n 否): " "" modify

        if [[ "${modify}" =~ ^[Yy]$ ]]; then
            echo "===> [agent] 您选择继续使用旧的配置文件[${config_file}]"
            exit 0
        else
            \cp -f "${config_file}" "${config_file_bak}"
            echo "===> [agent] 已经备份agent的配置文件到 ${config_file_bak}, 准备输入新的配置数据"
        fi
    else
        echo "===> [agent] 准备输入新的配置数据"
    fi

    gen_agent_config "${config_file}"

    cat <<EOF > "${agent_run_sh}"
#!/bin/bash

nohup ${NZ_AGENT_PATH}/nezha-agent \\
    -c ${config_file} \\
    > /dev/null 2>&1 &
EOF

    chmod +x "${agent_run_sh}"
}

modify_config() {
    echo "====> 开始准备修改，已知哪吒安装目录为[$1]"
    pre_check
    NZ_APP_PATH=$1

    prompt_input "===> 是否修改dashboard配置: " "N" modify
    if [[ "${modify}" =~ ^[Yy]$ ]]; then
        NZ_DASHBOARD_PATH="${NZ_APP_PATH}/dashboard"
        NZ_DASHBOARD_CONFIG_FILE="${NZ_DASHBOARD_PATH}/data/config.yaml"
        if [[ ! -f "${NZ_DASHBOARD_CONFIG_FILE}" ]]; then
            echo "dashboard的配置文件[${NZ_DASHBOARD_CONFIG_FILE}]不存在，请检查是否已经安装过了dashboard"
            exit 1
        fi

        echo "====> 准备开始修改dashboard配置文件[${NZ_DASHBOARD_CONFIG_FILE}]"
        modify_dashboard_config

        dashboard_pid=$(pgrep -f nezha-dashboard)
        if [[ -n "$dashboard_pid" ]]; then
            kill -9 "$dashboard_pid"
            echo "====> 关闭哪吒dashboard进程成功"
        fi
    fi

    prompt_input "===> 是否修改agent配置: " "N" modify
    if [[ "${modify}" =~ ^[Yy]$ ]]; then
        NZ_AGENT_PATH="${NZ_APP_PATH}/agent"
        agent_config_file="${NZ_AGENT_PATH}/config.yml"
        if [[ ! -f "${agent_config_file}" ]]; then
            echo "agent的配置文件[${agent_config_file}]不存在，请检查是否已经安装过了agent"
            exit 1
        fi

        echo "====> 准备开始修改agent配置文件[${agent_config_file}]"

        local agent_config_file_bak="${agent_config_file}.$(date +%Y_%m_%d_%H_%M)"
        \cp -f "${agent_config_file}" "${agent_config_file_bak}"
        gen_agent_config "${agent_config_file}"

        agent_pid=$(pgrep -f nezha-agent)
        if [[ -n "$agent_pid" ]]; then
            kill -9 "$agent_pid"
            echo "====> 关闭哪吒agent进程成功"
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

