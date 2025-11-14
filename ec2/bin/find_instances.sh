#!/usr/bin/env bash

INSTANCES_DIR="$HOME/.tabsdata/instances"
declare -A instances=()
instances=()

if [ ! -d "$INSTANCES_DIR" ]; then
    :
else
    for inst in "$INSTANCES_DIR"/*; do
        [ -d "$inst" ] || continue

        name=$(basename "$inst")
        cfg_path="$inst/workspace/config/proc/regular/apiserver/config/config.yaml"
        pid_path="$inst/workspace/work/proc/regular/apiserver/work/pid"

        # pid
        if [ -f "$pid_path" ]; then
            pid=$(cat "$pid_path") 
        else
            pid="None"
        fi

        # config ports
        if [ -f "$cfg_path" ]; then
            external_config_port=$(yamlz get --key addresses --path "$cfg_path")
            internal_config_port=$(yamlz get --key internal_addresses --path "$cfg_path")
        else
            external_config_port="None"
            internal_config_port="None"
        fi

        # status and arg ports
        status="Not_Running"
        external_arg_port="None"
        internal_arg_port="None"

        if [ "$pid" != "None" ]; then
            cmd=$(ps -p "$pid" -o args=)
            if [ -n "$cmd" ]; then
                status="Running"
                external_arg_port=$(yamlz get_arg --path "$cmd" --key addresses)
                internal_arg_port=$(yamlz get_arg --path "$cmd" --key internal-addresses)
            fi
        fi

        # fill arg ports from config if arg is missing
        if [[ "$external_config_port" != "None" && "$external_arg_port" == "None" ]]; then
            external_arg_port="$external_config_port"
        fi

        if [[ "$internal_config_port" != "None" && "$internal_arg_port" == "None" ]]; then
            internal_arg_port="$internal_config_port"
        fi

        inst_str="$name|$pid|$status|$external_config_port|$internal_config_port|$external_arg_port|$internal_arg_port"
        json=$(jq -n \
        --arg name "$name" \
        --arg pid "$pid" \
        --arg status "$status" \
        --arg cfg_ext "$external_config_port" \
        --arg cfg_int "$internal_config_port" \
        --arg arg_ext "$external_arg_port" \
        --arg arg_int "$internal_arg_port" \
        '{name:$name, pid:$pid, status:$status, cfg_ext:$cfg_ext, cfg_int:$cfg_int, arg_ext:$arg_ext, arg_int:$arg_int}')
        instances["$name"]="$json"
    done
fi


if (( ${#instances[@]} > 0 )); then
    printf '%s\n' "${instances[@]}"
fi




