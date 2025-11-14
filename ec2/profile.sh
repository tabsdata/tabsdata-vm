sudo tee /etc/profile.d/tabsdata.sh > /dev/null <<'EOF'
# ec2-user login behavior
if [ "$USER" = "ec2-user" ]; then
  if [ -z "$GUM_MESSAGE_SHOWN" ]; then
    export GUM_MESSAGE_SHOWN=1
    if [ -x /usr/local/bin/tabsdata/welcome.sh ]; then
      /usr/local/bin/tabsdata/welcome.sh
    fi
  fi
fi

# tabsdata login behavior
if [ "$USER" = "tabsdata" ]; then
  tabsdata() {
    if [ "$1" = "init" ]; then
      # adjust this path if needed
      source ~/bin/td-setup.sh
    else
      echo "tabsdata: unknown command '$1'"
      echo "try: tabsdata init"
    fi
  }
fi
EOF

sudo chmod +x /etc/profile.d/tabsdata.sh
