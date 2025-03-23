#!/bin/bash

log() {
    local level=$1
    shift
    case "$level" in
        "error") printf "\033[0;31m%s\033[0m\n" "$*" >&2 ;;
        "warn") printf "\033[0;33m%s\033[0m\n" "$*" ;;
        "info") printf "\033[0;32m%s\033[0m\n" "$*" ;;
        "info_input") printf "\033[0;32m%s\033[0m" "$*" ;;
        *) printf "%s\n" "$*" ;;
    esac
}

info() { log "info" "$@"; }
info_input() { log "info_input" "$@"; }
warn() { log "warn" "$@"; }
err() { log "error" "$@"; }

backup_config() {
    local file_path=$1
    local file_type=${2:-"配置"}

    [ -z "$file_path" ] && { err "文件路径不能为空"; return 1; }

    if [ -f "$file_path" ]; then
        local backup_path="${file_path}.$(date +%Y_%m_%d_%H_%M)"
        if cp -f "$file_path" "$backup_path"; then
            info "====> 已备份${file_type}文件到 ${backup_path}" >&2
            echo "$backup_path"
            return 0
        else
            err "备份${file_type}文件失败" >&2
            return 1
        fi
    else
        info "文件不存在，无需备份: $file_path" >&2
        echo ""
        return 0
    fi
}


config_backup=$(backup_config "test.sh" "配置文件");
if [ -n "$config_backup" ]; then
    echo "${config_backup}"
    if [ -f "$config_backup" ]; then
        echo "222222222222222: $config_backup"
    fi
fi