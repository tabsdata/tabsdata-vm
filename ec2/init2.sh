#!/usr/bin/env bash

for f in ~/bin/*.sh; do
  [ -f "$f" ] && source "$f"
done

tabsdata() {
if [ "$1" = "init" ]; then
    # adjust this path if needed
    source ~/bin/td-setup.sh
else
    echo "tabsdata: unknown command '$1'"
    echo "try: tabsdata init"
fi
}