#!/bin/bash
BASE_PATH=/usr/src/app/ATSoftwareDevelopmentTool
TARGET_PATH=/usr/src/app/ATSoftwareDevelopmentTool
FW_BUCKET="airtouch-firmware-production"
DRY_RUN=false

# Define color variables
RED='\033[0;31m'     # Red
GREEN='\033[1;32m'   # Green
YELLOW='\033[1;33m'  # Yellow
BLUE='\033[1;34m'    # Blue
NC='\033[0m'         # No Color (reset)

echo -e "${GREEN}        _      _                   _     ${NC}"
echo -e "${GREEN}   __ _(_)_ __| |_ ___  _   _  ___| |__  ${NC}"
echo -e "${GREEN}  / _\` | | '__| __/ _ \\| | | |/ __| '_ \\ ${NC}"
echo -e "${GREEN} | (_| | | |  | || (_) | |_| | (__| | | |${NC}"
echo -e "${GREEN}  \\__,_|_|_|   \\__\\___/ \\__,_|\\___|_| |_|${NC}"
echo -e "\n${YELLOW}    FactoryApp rsync script${NC}\n"

# options
echo -e "\n${GREEN}########################################################${NC}"
echo -e "Available servers options:"
echo -e "${GREEN}> ${YELLOW}pi-neo-1${NC}"
echo -e "${GREEN}> ${YELLOW}pi-neo-2${NC}"
echo -e "${GREEN}> ${YELLOW}pi-office${NC}"
echo -e "${GREEN}> ${YELLOW}testserver${NC}"
echo -e "\n${GREEN}########################################################${NC}"

# Ensure at least one argument is passed (the server name)
if [[ $# -lt 1 ]]; then
  echo -e "\n${RED}#### ERRORR ####${NC}"
  echo -e "${RED}Please supply server name to run...${NC}"
  echo -e "\nUsage: ${GREEN}bash $0 ${BLUE}<server name>${NC} [${YELLOW}--dry-run=true|false${NC}]\n"
  exit 1
fi

# Set server name
SERVER=$1
shift

# Parse remaining command-line options (e.g., --dry-run)
for arg in "$@"; do
  case $arg in
    --dry-run=true)
      DRY_RUN=true
      ;;
    --dry-run=false)
      DRY_RUN=false
      ;;
    *)
      echo -e "\n${RED}Unknown option:${YELLOW} $arg${NC}"
      echo -e "Usage: ${GREEN}$0 ${BLUE}<server name>${NC} [${YELLOW}--dry-run=true|false${NC}]\n"
      exit 1
      ;;
  esac
done

# Pull latest code from repo (dev branch)
cd $BASE_PATH
git reset --hard HEAD
git pull

# exit if no server define
if [[ -z "$SERVER" ]]; then
    echo -e "\n${RED}#### ERROR ####${NC}\nPlease supply a server name.\n Example: ${GREEN}$0 ${BLUE}<server name>${NC} [${YELLOW}--dry-run=true|false${NC}]\n"
    exit 1
fi

test_ssh() {
    echo -e "\nVerifying SSH connection to ${YELLOW}$SERVER${NC}..."

    ssh -q -o BatchMode=yes "$SERVER_IP" exit

    # Check the result of the SSH connection
    if [[ $? -eq 0 ]]; then
        echo -e "\n${GREEN}SSH connection to $SERVER was successful!. Continue next step...${NC}"
    else
        echo -e "\n${RED}Failed to connect to $SERVER via SSH.\nPlease make sure the Pi is online or the details is correct in ~/.ssh/config.${RED}"
        exit 1
    fi
}

# get_latest_fw() {
#     aws s3 cp s3://$FW_BUCKET/airtouch-ir/latest.txt $BASE_PATH/latest.txt
#     LATEST_FW=$(cat $BASE_PATH/latest.txt | tr -d '[:space:]')
#     aws s3 cp "s3://$FW_BUCKET/airtouch-ir/release/$LATEST_FW.dac" "$BASE_PATH/firmware/$LATEST_FW.dac"
# }

rsync_files() {
  # Determine if dry run flag should be included
  local dry_run_flag=""
  if [[ "$DRY_RUN" == "true" ]]; then
    dry_run_flag="--dry-run"
    echo -e "\n${YELLOW}#### Running in dry-run mode.. #####${NC}"
  fi

  rsync -avz $dry_run_flag --exclude 'device_data.txt' --exclude 'certs/' --exclude 'firmware/' --exclude '.git/' $BASE_PATH/ $SERVER_IP:$TARGET_PATH/
}

start_sync() {
    test_ssh
    rsync_files
}

case $SERVER in
    pi-neo-1)
        # SERVER_IP="100.113.142.62"
        SERVER_IP="pi-neo-1"
        echo -e "\nRsync to ${GREEN}$SERVER - $SERVER_IP${NC}"
        start_sync
        ;;
    pi-neo-2)
        SERVER_IP="pi-neo-2"
        echo -e "\nRsync to ${GREEN}$SERVER - $SERVER_IP${NC}"
        start_sync
        ;;
    pi-office)
        SERVER_IP="100.91.224.14"
        echo -e "\nRsync to ${GREEN}$SERVER - $SERVER_IP${NC}"
        start_sync
        ;;
    testserver)
        SERVER_IP="175.139.179.193"
        echo -e "\nRsync to ${GREEN}$SERVER - $SERVER_IP${NC}"
        start_sync
        ;;
    *)
        echo -e "\n${RED}Unknown server: $SERVER${NC}"
        exit 1
        ;;
esac
