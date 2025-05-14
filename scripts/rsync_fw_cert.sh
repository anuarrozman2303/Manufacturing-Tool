#!/bin/bash
# BASE_PATH=/usr/src/app/ATSoftwareDevelopmentTool
TARGET_PATH=/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool
MATTER_BUCKET=airtouch-production-matter-bin-artifacts-bucket
FW_SOURCE=/usr/src/app/ATSoftwareDevelopmentTool/scripts/fw
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
echo -e "\n${YELLOW}    Firmware, certs and DAC sync script${NC}\n"
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

  TEMPTARGET=/tmp/$ORDER_ID

  # if folder exist, delete first
  if [ -d "$TEMPTARGET" ]; then rm -rf "$TEMPTARGET"; fi

  mkdir -p "$TEMPTARGET/firmware/s3"
  mkdir -p "$TEMPTARGET/certs"

  echo -e "Copy ${GREEN}device_data.txt${NC} to ${YELLOW}$TEMPTARGET${NC}"
  aws s3 cp "s3://$MATTER_BUCKET/$ORDER_ID/device_data.txt" "$TEMPTARGET/"

  echo -e "Syncing contents of ${GREEN}s3://$MATTER_BUCKET/$ORDER_ID/certs/${NC} to ${YELLOW}$TEMPTARGET/certs/${NC}"
  echo -e "This could takes up to 15 minutes. Grab a coffee and relax..."
  aws s3 sync "s3://$MATTER_BUCKET/$ORDER_ID/" "$TEMPTARGET/certs/" --quiet

  echo -e "Remove unwanted files from ${YELLOW}$TEMPTARGET/certs/"
  find "$TEMPTARGET/certs/" -maxdepth 1 -type f -exec rm -f {} \;

  echo -e "Copy firmware files from ${GREEN}$FW_SOURCE${NC} to ${YELLOW}$TEMPTARGET/firmware/s3${NC}"
  cp $FW_SOURCE/*.bin $TEMPTARGET/firmware/s3/

  rsync -avz $DRY_RUN_FLAG --exclude '.git/' "$TEMPTARGET/" "$SELECTED_IP:$TARGET_PATH/"
}

cleanup() {
  echo -e "Removing temp folder ${GREEN}$TEMPTARGET${NC}"
  rm -rf "$TEMPTARGET"
  echo -e "${GREEN}Task completed!${NC}"
}

start_sync() {
    check_ssh_config
    test_ssh_connection
    rsync_files
    cleanup
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

      # Get ORDER_ID
      while true; do
        read -p "Please key in the ID for the bin: " ORDER_ID

        # Check if ORDER_ID is empty
        if [[ -z "$ORDER_ID" ]]; then
          echo -e "${RED}ID cannot be empty. Please enter a valid ID.${NC}"
          continue
        fi

        # Confirm the entered ORDER_ID
        read -p "You entered ${YELLOW}$ORDER_ID${NC}. Is this correct? (Y/N): " CONFIRM_ORDER_ID

        if [[ ${CONFIRM_ORDER_ID,,} == "y" ]]; then
          echo -e "\nOrder ID ${YELLOW}$ORDER_ID${NC} confirmed..."
          break  # Exit both ORDER_ID and main loops to proceed
        elif [[ ${CONFIRM_ORDER_ID,,} == "n" ]]; then
          echo -e "${YELLOW}Re-enter the ID.${NC}"
        else
          echo -e "${RED}Invalid choice. Please enter Y or N.${NC}"
        fi
      done

      read -p "Are you sure you want to proceed with this IP address (${BLUE}$SELECTED_IP${NC}) and Order ID (${YELLOW}$ORDER_ID${NC})? (yes/no): " CONFIRMATION

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

