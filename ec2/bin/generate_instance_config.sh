#!/usr/bin/env bash

get_running_ports() {
  declare -A port_map
  local name pid status cfg_ext cfg_int arg_ext arg_int
  port_map=()
  local instances=()
    if [ -z "$1" ]; then
        mapfile -t instances_temp < <(~/bin/find_instances.sh | jq -c .)
    else
        local -n instances_temp=$1
    fi

  local ports=()
  

   for json in "${instances_temp[@]}"; do

        name=$(jq -r '.name' <<< "$json")
        status=$(jq -r '.status' <<< "$json")
        pid=$(jq -r '.pid' <<< "$json")
        cfg_ext=$(jq -r '.cfg_ext' <<< "$json")
        cfg_int=$(jq -r '.cfg_int' <<< "$json")
        arg_ext=$(jq -r '.arg_ext' <<< "$json")
        arg_int=$(jq -r '.arg_int' <<< "$json")
        
        ext_port="${arg_ext##*:}"
        int_port="${arg_int##*:}"

        json=$(echo "$json" | jq --arg ext "$ext_port" --arg int "$int_port" \
        '.external_port = $ext | .internal_port = $int')
    

        if [ "$status" = "Running" ]; then
            port_map["$name"]="$json"
        fi
    done

  printf '%s\n' "${port_map[@]}"
}

validate_port() {
  local port="$1"
  if [[ "$port" =~ ^[0-9]+$ ]] && (( port >= 1 && port <= 65535 )); then
    echo "true"
  else
    echo "false"
  fi
}

port_in_use() {
  local name pid status cfg_ext cfg_int arg_ext arg_int
  local port="$1"
  local compare_port
  local port_type="$2"
  local curr_instance_name="$3"
  local used=()
  local arr=()
  mapfile -t used < <(get_running_ports | jq -c .)

  for json in "${used[@]}"; do
    name=$(jq -r '.name' <<< "$json")
    status=$(jq -r '.status' <<< "$json")
    pid=$(jq -r '.pid' <<< "$json")
    cfg_ext=$(jq -r '.cfg_ext' <<< "$json")
    cfg_int=$(jq -r '.cfg_int' <<< "$json")
    arg_ext=$(jq -r '.arg_ext' <<< "$json")
    arg_int=$(jq -r '.arg_int' <<< "$json")
    ext_port=$(jq -r '.external_port' <<< "$json")
    int_port=$(jq -r '.internal_port' <<< "$json")

    if [[ "$curr_instance_name" = "$name" ]]; then
        continue
    elif [[ "$ext_port" = "$port" ]]; then
        echo "$name"
        return 0 # Port is in use
    elif [[ "$int_port" = "$port" ]]; then
        echo "$name"
        return 0 # Port is in use
    fi
  done
  return 1  # not in use
}

prompt_for_free_port() {
  local port="$1"
  local label="$2"
  local port_type="$3"
  local instance_name="$4"
  local new_port=$port

  while true; do
    if [ "$(validate_port "$new_port")" = "true" ]; then
      gum style \
        --border rounded \
        --padding "1 2" \
        --border-foreground "#f97316" \
        "Port $new_port is unavailable for $label (in use by '$instance_name'). Please provide a different port." >&2
    fi

    new_port=$(gum input --prompt "> " --placeholder "$port")

    # validate format
    if [ "$(validate_port "$new_port")" != "true" ]; then
      gum style --foreground "#f97316" "That is not a valid port number. Try again." >&2
      continue
    fi

    # check availability
    if instance_using_port=$(port_in_use "$new_port" "$port_type"); then
      continue
    fi
    echo "$new_port"
    return 0
  done 
}

select_config() {
  local selected="$1"
  local instance_name arg_ext arg_int config_type
  local full_arg_ext full_arg_int

  if [[ "$selected" == "Create a New Instance" ]]; then
    gum style \
      --border normal \
      --margin "1 2" \
      --padding "1 2" \
      --border-foreground "#0f766e" \
      --align left \
      "💡 Provide a Name for your Instance." \
      "" \
      "You may leave this blank to use the default instance name 'tabsdata'."

    instance_name=$(gum input --prompt "> ")
    instance_name=${instance_name:-tabsdata}

    while [ -d "$HOME/.tabsdata/instances/$instance_name" ]; do
        gum style --foreground "#f97316" "That instance name already exists. Try another."
        instance_name=$(gum input --prompt "> ")
    done

    # defaults for new instances
    arg_ext="2457"
    arg_int="2458"
    full_arg_ext="$PRIVATE_IP:2457"
    full_arg_int="127.0.0.1:2458"

  else
    # selected is JSON from instance_map
    instance_name=$(jq -r '.name' <<< "$selected")
    arg_ext=$(jq -r '.arg_ext' <<< "$selected")
    arg_int=$(jq -r '.arg_int' <<< "$selected")

    full_arg_ext="$arg_ext"
    full_arg_int="$arg_int"

    # grab just port if in host:port form
    arg_ext=${arg_ext#*:}
    arg_int=${arg_int#*:}

    if [ "$(validate_port "$arg_ext")" != "true" ]; then
      arg_ext="2457"
      full_arg_ext="$PRIVATE_IP:$arg_ext"
    fi

    if [ "$(validate_port "$arg_int")" != "true" ]; then
      arg_int="2458"
      full_arg_int="127.0.0.1:$arg_int"
    fi
  fi

  # check current defaults against running ports
  # external
  


  if gum confirm "By default, the Tabsdata server $instance_name is set up on:

• Port $arg_ext for external connections
• Port $arg_int for internal connections

Would you like to use the default configuration, or set custom ports?" \
    --affirmative="Use Defaults" \
    --negative="Set Custom Ports" \
    --prompt.foreground="#10b981" \
    --selected.background="22" \
    --unselected.background="235" \
    --selected.foreground="230" \
    --padding="1 2"
  then
    config_type="default"
  else
    config_type="custom"
  fi

  if [[ "$config_type" == "default" ]]; then
    external_port="$arg_ext" 
    internal_port="$arg_int"

    if instance_using_port=$(port_in_use "$external_port" "ext" "$instance_name"); then
      external_port=$(prompt_for_free_port "$external_port" "external connections" "ext" "$instance_using_port")
      full_arg_ext="$PRIVATE_IP:$arg_ext"
    fi
    

    if instance_using_port=$(port_in_use "$internal_port" "int" "$instance_name"); then
      internal_port=$(prompt_for_free_port "$internal_port" "internal connections" "int" "$instance_using_port")
      full_arg_int="127.0.0.1":$arg_int
    fi

  else
    # externa
    gum style --margin "1 2" "Please provide an External Port"
    external_port=$(gum input --prompt "> " --placeholder "$arg_ext")

    if instance_using_port=$(port_in_use "$external_port" "ext" "$instance_name"); then
      external_port=$(prompt_for_free_port "$external_port" "external connections" "ext" "$instance_using_port")
      full_arg_ext="$PRIVATE_IP:$external_port"
    fi

  # internal
    gum style --margin "1 2" "Please provide an Internal Port"
    internal_port=$(gum input --prompt "> " --placeholder "$arg_int")

    if instance_using_port=$(port_in_use "$internal_port" "int" "$instance_name"); then
      internal_port=$(prompt_for_free_port "$internal_port" "internal connections" "int" "$instance_using_port")
      full_arg_int="127.0.0.1:$internal_port"
    fi
  fi

  while [ "$external_port" = "$internal_port" ]; do
    gum style --margin "1 2" "It is not recommended to use the same port for external and internal connections
    Please choose another port" >&2
    internal_port=$(gum input --prompt "> " --placeholder "$arg_int")

    if instance_using_port=$(port_in_use "$internal_port" "int" "$instance_name"); then
      internal_port=$(prompt_for_free_port "$internal_port" "internal connections" "int" "$instance_using_port")
      full_arg_int="127.0.0.1:$internal_port"
    fi
  done

  # return as JSON
  result=$(jq -n \
    --arg name "$instance_name" \
    --arg external "$external_port" \
    --arg internal "$internal_port" \
    '{name:$name, external_port:$external, internal_port:$internal}')
}
