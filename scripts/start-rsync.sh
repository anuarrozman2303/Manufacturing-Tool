#!/bin/bash
#!/bin/bash
BASE_PATH=/usr/src/app/ATSoftwareDevelopmentTool
TARGET_PATH=/usr/src/app/ATSoftwareDevelopmentTool
DRY_RUN=false

# Define color variables
RED=$(printf '\033[0;31m')     # Red
GREEN=$(printf '\033[1;32m')   # Green
YELLOW=$(printf '\033[1;33m')  # Yellow
BLUE=$(printf '\033[1;34m')    # Blue
NC=$(printf '\033[0m')         # No Color (reset)

echo -e "${GREEN}        _      _                   _     ${NC}"
echo -e "${GREEN}   __ _(_)_ __| |_ ___  _   _  ___| |__  ${NC}"
echo -e "${GREEN}  / _\` | | '__| __/ _ \\| | | |/ __| '_ \\ ${NC}"
echo -e "${GREEN} | (_| | | |  | || (_) | |_| | (__| | | |${NC}"
echo -e "${GREEN}  \\__,_|_|_|   \\__\\___/ \\__,_|\\___|_| |_|${NC}"
echo -e "\n${YELLOW}    FactoryApp rsync script${NC}\n"
echo -e "\n${GREEN}########################################################${NC}\n"

mapfile -t IP_ARRAY < iplist.txt

display_ip_list() {
  echo "Available servers:"
  for i in "${!IP_ARRAY[@]}"; do
    # Split each line into IP and DESCRIPTION
    IP=$(echo "${IP_ARRAY[$i]}" | awk '{print $1}')
    DESCRIPTION=$(echo "${IP_ARRAY[$i]}" | awk '{print $2}')
    echo -e "${GREEN}$((i+1))${NC} > ${YELLOW}$IP${NC} : $DESCRIPTION"
  done
  echo -e "To ${RED}quit${NC} type either ${YELLOW}Q${NC} or ${YELLOW}q${NC} to quit\n"
}

check_ssh_config() {
  # Check if the IP is already in ~/.ssh/config
  if grep -q "Host $SELECTED_IP" ~/.ssh/config; then
    echo "SSH config for $SELECTED_IP already exists."
  else
    echo -e "${RED}ERROR!${NC} No config found in ${BLUE}~/.ssh/config${NC} for ${YELLOW}$SELECTED_IP${NC}"
    echo -e "Please add the config in ${BLUE}~/.ssh/config${NC} first and try again" 

    cat <<EOL 

${BLUE}## Start config${NC}
Host $SELECTED_IP
  Hostname $SELECTED_IP
  Port <ssh port>
  User <username>
  IdentityFile <ssh private key>
  IdentitiesOnly yes
${BLUE}## End config${NC}


EOL

  exit 1
  fi
}

test_ssh_connection() {
    echo -e "\nVerifying SSH connection to ${YELLOW}$SELECTED_IP${NC}..."

    ssh -q -o BatchMode=yes "$SELECTED_IP" exit

    # Check the result of the SSH connection
    if [[ $? -eq 0 ]]; then
        echo -e "\n${GREEN}SSH connection to $SELECTED_IP was successful!. Continue next step...${NC}"
    else
        echo -e "\n${RED}Failed to connect to $SELECTED_IP via SSH.\nPlease make sure the Pi is online or the details is correct in ~/.ssh/config.${RED}"
        exit 1
    fi
}

rsync_files() {
  # Determine if dry run flag should be included
  local DRY_RUN_FLAG=""
  if [[ "$DRY_RUN" == "true" ]]; then
    DRY_RUN_FLAG="--dry-run"
    echo -e "\n${YELLOW}#### Running in dry-run mode.. #####${NC}"
  fi

  rsync -avz $DRY_RUN_FLAG --exclude 'device_data.txt' --exclude 'certs/' --exclude 'firmware/' --exclude '.git/' "$BASE_PATH/" "$SELECTED_IP:$TARGET_PATH/"
}

start_sync() {
    check_ssh_config
    test_ssh_connection
    rsync_files
}

while true; do
  display_ip_list

  # Prompt user to choose an IP address
  read -p "Choose an IP address (enter the number): " CHOICE

  if [[ ${CHOICE,,} == "q" ]]; then
    echo -e "You choose to quit. Goodbye..."
    exit 1
  else
    if [[ $CHOICE -gt 0 && $CHOICE -le ${#IP_ARRAY[@]} ]]; then
      SELECTED_IP=$(echo "${IP_ARRAY[$((CHOICE-1))]}" | awk '{print $1}')
      echo -e "\nYou selected: ${BLUE}$SELECTED_IP${NC}\n"

      read -p "Would you like to test sync first using ${YELLOW}--dry-run${NC}? (yes/no) Default=no : " DRYRUN

      if [[ "$DRYRUN" == "yes" ]]; then
        echo -e "\nOk rsync will run with ${YELLOW}--dry-run${NC}..."
        DRY_RUN="true"
      fi

      read -p "Are you sure you want to proceed with this IP address? (yes/no): " CONFIRMATION

      if [[ "$CONFIRMATION" == "yes" ]]; then
        echo -e "\nProceeding with ${YELLOW}$SELECTED_IP${NC}..."
        break
      else
        echo -e "\n${YELLOW}Selection canceled. Please choose again.${NC}"
      fi
    else
      echo "${RED}Invalid choice. Please select a valid number.${NC}"
    fi
  fi
done

start_sync

# # Verification step: Attempt to connect via SSH
# echo "Verifying SSH connection to $SELECTED_IP..."

# ssh -q -o BatchMode=yes "$SELECTED_IP" exit

# # Check the result of the SSH connection
# if [[ $? -eq 0 ]]; then
#   echo "SSH connection to $SELECTED_IP was successful!. Continue next step..."
# else
#   echo "Failed to connect to $SELECTED_IP via SSH. Please make sure details is correct in ~/.ssh/config"
# fi
