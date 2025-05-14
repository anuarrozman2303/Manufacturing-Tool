#!/bin/bash

# Script to set up Samba share on Raspberry Pi

# Variables
SHARED_FOLDER_PATH="/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result"
SAMBA_CONF="/etc/samba/smb.conf"
SAMBA_USER="airdroitech"

# Step 1: Update package list and install Samba server
echo "Updating package list..."
sudo apt update -y

echo "Installing Samba server..."
sudo apt install samba -y

# Step 2: Configure Samba shared folder
echo "Configuring Samba shared folder..."
{
    echo "[SharedFolder]"
    echo "path = $SHARED_FOLDER_PATH"
    echo "browseable = yes"
    echo "read only = no"
    echo "writable = yes"
    echo "guest ok = yes"
    echo "create mask = 0777"
    echo "directory mask = 0777"
} | sudo tee -a $SAMBA_CONF

# Step 3: Restart Samba server
echo "Restarting Samba server..."
sudo systemctl restart smbd

# Step 4: Add Samba user
echo "Adding Samba user..."
sudo smbpasswd -a $SAMBA_USER

echo "Samba share setup is complete. You can access it from Windows by mapping the network drive."
