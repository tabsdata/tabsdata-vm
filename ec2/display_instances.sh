#!/usr/bin/env bash
make_card() {
  local name="$1"
  local status_color="$2"
  local status_text="$3"
  local ext="$4"
  local int="$5"

  gum style \
    --border rounded \
    --border-foreground "$status_color" \
    --padding "0 1" \
    "$(gum style --bold --foreground "$status_color" "📦 $name  $status_text")" \
    "$(gum style --foreground '#a1a1aa' "   ext: $ext")" \
    "$(gum style --foreground '#a1a1aa' "   int: $int")"
}


display_instances() {
    local instances_temp
    local name pid status cfg_ext cfg_int arg_ext arg_int

    if [ -z "$1" ]; then
        mapfile -t instances_temp < <(~/bin/find_instances.sh | jq -c .)
    else
        local -n instances_temp=$1
    fi
    
    [ ${#instances_temp[@]} -eq 0  ] && { echo "No instances found."; return 0; }

    stopped_block=""
    running_block=""

    for json in "${instances_temp[@]}"; do

        name=$(jq -r '.name' <<< "$json")
        status=$(jq -r '.status' <<< "$json")
        pid=$(jq -r '.pid' <<< "$json")
        cfg_ext=$(jq -r '.cfg_ext' <<< "$json") 
        cfg_int=$(jq -r '.cfg_int' <<< "$json")
        arg_ext=$(jq -r '.arg_ext' <<< "$json")
        arg_int=$(jq -r '.arg_int' <<< "$json")

        if [ "$status" = "Running" ]; then
            box=$(gum style \
                --border rounded \
                --padding "0 1" \
                --border-foreground "#22c55e" \
                "$(gum style --bold --foreground '#22c55e' "$name  ● Running")" \
                "$(gum style --foreground '#e2e8f0' "running on → ext: $arg_ext")" \
                "$(gum style --foreground '#e2e8f0' "running on → int: $arg_int")")
            running_block="${running_block}"$'\n'"$box"
        else
            box=$(gum style \
                --border rounded \
                --padding "0 1" \
                --border-foreground "#ef4444" \
                "$(gum style --bold --foreground '#ef4444' "$name  ○ Not running")" \
                "$(gum style --foreground '#e2e8f0' "configured on → ext: $cfg_ext")" \
                "$(gum style --foreground '#e2e8f0' "configured on → int: $cfg_int")")
            stopped_block="${stopped_block}"$'\n'"$box"
        fi
    done
    # done <<< "$instances"

    # Display all instances in a single styled gum box
    gum style \
    --border rounded \
    --margin "1 2" \
    --padding "1 2" \
    --align left \
    --border-foreground "#0f766e" \
    "$(gum style --bold --foreground '#22c55e' '📦 Tabsdata Instances')" \
    "" \
    "$(gum style --foreground '#e2e8f0' 'You have the following Tabsdata instances available:')" \
    "" \
    "$(gum join --horizontal "$stopped_block" "$running_block")"

}
