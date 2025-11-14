#!/usr/bin/env bash

source ~/bin/generate_instance_config.sh
source ~/bin/display_instances.sh 

set +m

start_gum_spinner() {
  SPINNER_TITLE="$1"
  gum spin --spinner dot --title "⏳ $SPINNER_TITLE" -- sleep 20 </dev/null &
  SPINNER_PID=$!
}

stop_gum_spinner() {
    sleep .5
  local show="$1" # Corrected: properly assign the first argument to 'show'
  if [ -n "${SPINNER_PID:-}" ]; then
    # Send TERM signal (15) for graceful shutdown.
    # This allows the process to catch the signal and perform cleanup.
    kill -TERM "$SPINNER_PID" >/dev/null 2>&1 || true
    
    # Wait for the process to actually terminate.
    # This is crucial to ensure cleanup routines (if any) have a chance to run.
    wait "$SPINNER_PID" 2>/dev/null || true
    
    # Add a very short sleep. This is a heuristic to give the terminal
    # a moment to process any final output or for gum to finish its cleanup,
    # especially if there's a race condition with terminal responses.
    sleep 0.05
  fi
  # Check if 'show' is "0" or if no argument was provided (i.e., "$show" is empty)
  if [ "$show" = "0" ] || [ -z "$show" ]; then # Corrected: use "$show" and proper spacing
    echo "✅ $SPINNER_TITLE"
  fi
}

kill_legacy_processes() {
# 1. get the PIDs bound to active instances 
mapfile -t active_pids < <(~/bin/find_instances.sh | jq -r '.pid')

# build a  lookup
declare -A keep
for pid in "${active_pids[@]}"; do
    [ -n "$pid" ] && keep["$pid"]=1
done

# 2. get every apiserver pid listening on a socket
mapfile -t ss_pids < <(ss -tulnp | awk '/apiserver/ {
  match($0, /pid=([0-9]+)/, a)
  if (a[1] != "") print a[1]
}' | sort -u)

# 3. kill the ones that are not in find_instances
  for pid in "${ss_pids[@]}"; do
    if [ -z "${keep[$pid]:-}" ]; then
      echo "💀 Killing legacy apiserver (PID $pid)"
      kill -9 "$pid" 
    fi
  done

  #find pids where only an external connection is active
  mapfile -t lonely_pids < <(
  ss -tulnp | awk '/apiserver/ {
    match($0, /pid=([0-9]+)/, a)
    if (a[1] != "") print a[1]
  }' \
  | sort \
  | uniq -c \
  | awk '$1 == 1 { print $2 }'
)

# kill solo pids
for pid in "${lonely_pids[@]}"; do
  echo "killing stray apiserver pid $pid"
  sudo kill -9 "$pid" 2>/dev/null || true
done
}

export PUBLIC_HOSTNAME=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)
export PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
export PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

TITLE_STYLE='--foreground="#ffffff" --background="#FFAB40" --bold'
BODY_STYLE='--foreground="#ffffff" --background="#FFAB40"'


start_gum_spinner "Activating Virtual Environment"
{
if [ ! -d "$HOME/tabsdata-env" ]; then 
    python3.12 -m venv "$HOME/tabsdata-env"
    source ~/tabsdata-env/bin/activate
    python3.12 -m pip3.12 install "tabsdata[all]"
else
    if [ -z "$VIRTUAL_ENV" ]; then
        source "$HOME/tabsdata-env/bin/activate"
    fi
fi
} >/dev/null 2>&1
stop_gum_spinner


gum style \
  --border double \
  --margin "1 2" \
  --padding "1 2" \
  --align center \
  --border-foreground "#FFAB40" \
  "$(cat bin/logo.txt)" \
  "" \
  "$(gum style $TITLE_STYLE 'Welcome to Tabsdata AMI')" \
  "" \
  "$(gum style $BODY_STYLE 'This AMI is designed to quickly set up a Tabsdata instance in EC2.')" \
  "$(gum style $BODY_STYLE 'You can either use the Quickstart for automatic setup or configure it manually.')"

# 2. ask user how they’d like to proceed

choice=$(gum choose \
  --cursor "▶ " \
  "Quickstart (recommended)" \
  "I'd rather do it myself")

if [ "$choice" != "Quickstart (recommended)" ]; then
  gum style \
    --border rounded \
    --margin "1 2" \
    --padding "1 2" \
    --align left \
    --border-foreground "#FFAB40" \
    "$(gum style --foreground "#FFAB40" '📘 Tabsdata Manual Setup')" \
    "" \
    "$(gum style --foreground "#999999" 'You can find detailed instructions for setting up Tabsdata in our documentation:')" \
    "$(gum style --foreground "#FFAB40" 'https://docs.tabsdata.com/latest/guide/01_overview/main.html')" \
    "" \
    "$(gum style --foreground "#999999" 'If you change your mind later, just run:')" \
    "$(gum style --foreground "#FFAB40" 'tabsdata init')"
  return 0
fi

start_gum_spinner "Killing Legacy Processes"
{
kill_legacy_processes
} >/dev/null 2>&1
stop_gum_spinner



mapfile -t instances < <(~/bin/find_instances.sh | jq -c .)


if [ ${#instances[@]} -eq 0 ]; then
    if gum confirm "Looks like you don't have any Tabsdata instances set up, would you like to create your first one?" \
    --affirmative="Yes Please" \
    --negative="Nah" \
    --prompt.foreground="#FFAB40" \
    --selected.background="#FFAB40" \
    --unselected.background="#999999" \
    --selected.foreground="#ffffff" \
    --padding="1 2"; then
        select_config "Create a New Instance"
    else
        gum style \
        --border rounded \
        --margin "1 2" \
        --padding "1 2" \
        --align left \
        --border-foreground "#FFAB40" \
        "$(gum style --foreground "#FFAB40" 'No Problem!')" \
        "$(gum style --foreground "#999999" 'If you change your mind later, just run:')" \
        "$(gum style --foreground "#FFAB40" 'tabsdata init')"
        return 0
    fi
else
    start_gum_spinner "Pulling Existing Tabsdata Instance Data"
    display_instances 
    stop_gum_spinner 1

    
    choices=()
    instance_names=()
    spaced_cards=()
    declare -A instance_map
    instance_map=()

    for inst in "${instances[@]}"; do
        name=$(jq -r '.name' <<< "$inst")
        status=$(jq -r '.status' <<< "$inst")
        arg_int=$(jq -r '.arg_int' <<< "$inst")
        arg_ext=$(jq -r '.arg_ext' <<< "$inst")

        if [ "$status" = "Running" ]; then
            c="$(make_card "$name" "#22c55e" "● Running" "$arg_ext" "$arg_int")"
        else
            c="$(make_card "$name" '#ef4444' '○ Not Running' "$arg_ext" "$arg_int")"
        fi
        
        readarray -t lines <<< "$c"

        # build a new set of lines with indentation on lines > 0
        new_lines=()
        for i in "${!lines[@]}"; do
            if (( i == 0 )); then
                new_lines+=("${lines[$i]}")
            else
                new_lines+=("  ${lines[$i]}")
            fi
        done
        indented_card=$(printf "%s\n" "${new_lines[@]}")
        spaced_cards+=("$indented_card")

        selected_cache=$(gum choose \
        --cursor.foreground "#22c55e" \
        --select-if-one \
        --header "Would you like to start one of them?" \
        "${spaced_cards[@]: -1:2}")
        selected_cache=$(printf '%s' "$selected_cache" | sed 's/\x1B\[[0-9;]*[A-Za-z]//g')
        safe_selected=$(
            printf '%s' "$selected_cache" \
            | base64 \
            | tr -d '\n='
        )

        instance_map["$safe_selected"]="$inst"
    done

    cards=()
    new_card=$(gum style \
    --border rounded \
    --border-foreground "#38bdf8" \
    --padding "0 1" \
    "$(gum style --bold --foreground '#38bdf8' '➕  Create a New Instance')" \
    "$(gum style --foreground '#a1a1aa' '   Start a brand-new Tabsdata instance')")

    exit_card=$(gum style \
    --border rounded \
    --border-foreground "#f87171" \
    --padding "0 1" \
    "$(gum style --bold --foreground '#f87171' '🚪  Exit Quickstart')" \
    "$(gum style --foreground '#a1a1aa' '   Close the setup wizard and return to shell')")

    # add them to your choices list
    cards+=("$new_card")

    cards+=("$exit_card")

    for w in "${!cards[@]}"; do
        c="${cards[$w]}" 
        readarray -t lines <<< "$c"

        # build a new set of lines with indentation on lines > 0
        new_lines=()
        for i in "${!lines[@]}"; do
            if (( i == 0 )); then
                new_lines+=("${lines[$i]}")
            else
                new_lines+=("  ${lines[$i]}")
            fi
        done
        indented_card=$(printf "%s\n" "${new_lines[@]}")
        spaced_cards+=("$indented_card")

        
        # map each indented card to an action
        if [ "$w" = "0" ]; then
            selected_cache=$(gum choose \
            --cursor.foreground "#22c55e" \
            --select-if-one \
            --header "Would you like to start one of them?" \
            "${spaced_cards[@]: -1:2}")
            selected_cache=$(printf '%s' "$selected_cache" | sed 's/\x1B\[[0-9;]*[A-Za-z]//g')
            safe_selected=$(
                printf '%s' "$selected_cache" \
                | base64 \
                | tr -d '\n='
            )
            instance_map["$safe_selected"]="Create a New Instance"
        elif [ "$w" = "1" ]; then
            selected_cache=$(gum choose \
            --cursor.foreground "#22c55e" \
            --select-if-one \
            --header "Would you like to start one of them?" \
            "${spaced_cards[@]: -1:2}")
            selected_cache=$(printf '%s' "$selected_cache" | sed 's/\x1B\[[0-9;]*[A-Za-z]//g')
            safe_selected=$(
                printf '%s' "$selected_cache" \
                | base64 \
                | tr -d '\n='
            )
            instance_map["$safe_selected"]="Exit Quickstart"
        fi

    done

    

    # now show menu
    selected=$(gum choose \
        --cursor.foreground "#22c55e" \
        --header "Would you like to start one of them?" \
        "${spaced_cards[@]}")
    safe_selected_result=$(
        printf '%s' "$selected" \
        | base64 \
        | tr -d '\n='
    )

    json="${instance_map["$safe_selected_result"]}"


    if [ "$json" != "Create a New Instance" ] && [ "$json" != "Exit Quickstart" ]; then
        name=$(jq -r '.name' <<< "$json")
        pid=$(jq -r '.pid' <<< "$json")
        status=$(jq -r '.status' <<< "$json")
        cfg_ext=$(jq -r '.cfg_ext' <<< "$json")
        cfg_int=$(jq -r '.cfg_int' <<< "$json")
        arg_ext=$(jq -r '.arg_ext' <<< "$json")
        arg_int=$(jq -r '.arg_int' <<< "$json")
    elif  [ "$json" = "Exit Quickstart" ]; then
        return 0
    fi

    select_config "$json" 
fi


instance_name=$(jq -r '.name' <<< "$result")
external_port=$(jq -r '.external_port' <<< "$result")
internal_port=$(jq -r '.internal_port' <<< "$result")


start_gum_spinner "Killing Legacy Processes"
{
kill_legacy_processes
} >/dev/null 2>&1
stop_gum_spinner




start_gum_spinner "Initializing Tabsdata Instance"
{
if [ ! -d "$HOME/.tabsdata/instances/$instance_name" ]; then
    tdserver create --instance $instance_name
fi 
} >/dev/null 2>&1
stop_gum_spinner

if [ -f "$HOME/cert.pem" ]; then 
    export GENERATED_PUBLIC_HOSTNAME=$(openssl x509 -in cert.pem -noout -subject | sed -n 's/.*CN=\(.*\)/\1/p')
    export GENERATED_PUBLIC_IP=$(openssl x509 -in cert.pem -noout -ext subjectAltName | grep -oP 'IP Address:\K[0-9.]*')
else
    export GENERATED_PUBLIC_HOSTNAME="None"
    export GENERATED_PUBLIC_IP="None"
fi


start_gum_spinner "Generating HTTPS Certificate"
{
if [ "$GENERATED_PUBLIC_HOSTNAME:$GENERATED_PUBLIC_IP" != "$PUBLIC_HOSTNAME:$PUBLIC_IP" ]; then
    cd
    export NAME=${PUBLIC_HOSTNAME}
    export SUBJ="/CN=${NAME}"
    export CONFIG="[dn]\nCN=${NAME}\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:${NAME},IP:${PUBLIC_IP}\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth"

    printf "%b" "${CONFIG}" | openssl \
        req -x509 \
        -out cert.pem \
        -keyout key.pem \
        -newkey rsa:4096 \
        -nodes -sha256 \
        -subj "${SUBJ}" \
        -extensions EXT \
        -config -

    echo "Certificate created: $(pwd)/key.pem and $(pwd)/cert.pem"
else
    echo "Certificate already exists, skipping creation."
fi
} >/dev/null 2>&1
stop_gum_spinner

export SSL_PATH="$HOME/.tabsdata/instances/$instance_name/workspace/config/ssl"


start_gum_spinner "Configuring HTTPS Certificates to Tabsdata Instance"
{
if [ ! -f "$SSL_PATH/key.pem" ] || [ ! -f "$SSL_PATH/cert.pem" ]; then
    cp key.pem cert.pem ~/.tabsdata/instances/$instance_name/workspace/config/ssl/
elif ! cmp -s $SSL_PATH/cert.pem cert.pem || ! cmp -s $SSL_PATH/key.pem key.pem; then
    cp key.pem cert.pem ~/.tabsdata/instances/$instance_name/workspace/config/ssl/
else
    echo "https config up-to-date"
fi
} >/dev/null 2>&1 
stop_gum_spinner

export CONFIG_PATH="$HOME/.tabsdata/instances/$instance_name/workspace/config/proc/regular/apiserver/config/config.yaml"
export TDSERVER_IP=$(yamlz get --key addresses --path "$CONFIG_PATH" | sed "s/:.*//")


start_gum_spinner "Binding Tabsdata Server to EC2 IP Address"
{
yamlz set --path "$CONFIG_PATH" --key addresses --value "$PRIVATE_IP:$external_port" --type "list"
yamlz set --path "$CONFIG_PATH" --key internal_addresses --value "127.0.0.1:$internal_port" --type "list"
} >/dev/null 2>&1
stop_gum_spinner 




start_gum_spinner "Starting Tabsdata Server"

{
  instance_name=tabsdata
  LOGFILE="$HOME/.tabsdata/instances/$instance_name/workspace/work/proc/regular/apiserver/work/log/td.log"

  SUCCESS_RE="Tabsdata instance '([^']+)' started with pid '([0-9]+)'"
  ERROR_RE="Error creating API Server: Failed to bind to address \[([^]]+)\]: Address in use"

  timeout 30 tdserver restart --instance "$instance_name" &
  TD_PID=$!

  # single tail feeding the loop
  timeout 30 tail -n0 -F "$LOGFILE" | while IFS= read -r line; do
    echo "$line"

    if [[ $line =~ $SUCCESS_RE ]]; then
      echo "found"
      break
    fi

    if [[ $line =~ $ERROR_RE ]]; then
      echo "killing processes"

      kill "$TD_PID"
      tdserver stop --instance $instance_name

      kill_legacy_processes
      pkill -P $$ tail 2>/dev/null || true
      break
    fi
  done

  # only wait if tdserver is still alive
  if kill -0 "$TD_PID" 2>/dev/null; then
    wait "$TD_PID"
  fi
  tdserver start --instance $instance_name
}

stop_gum_spinner






display_instances

gum style \
  --border double \
  --border-foreground "#FFAB40" \
  --align center \
  --width 70 \
  --margin "1 2" \
  --padding "1 3" \
  "✅ Tabsdata Instance $instance_name is running!" \
  "" \
  "You can access the Tabsdata UI through the link below:" \
  "    👉  https://$PUBLIC_IP:$external_port"

# trap -  SIGINT SIGTERM
