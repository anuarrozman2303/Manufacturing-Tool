#!/bin/bash

# Combined Raspberry Pi Setup, Samba Share, and I2C Configuration Script

# Function to check if a command succeeded
check_command() {
    if [ $? -ne 0 ]; then
        echo "Error: Command failed. Exiting script."
        exit 1
    fi
}

# Step 1: Setup Directory Ownership
echo "Setting up directory ownership..."
sudo chown -R airdroitech:airdroitech /usr/src
mkdir -p /usr/src/app
check_command

# Step 2: Enable pip for Package Management
echo "Configuring pip for package management..."
{
    echo "[global]"
    echo "break-system-packages=true"
} | sudo tee /etc/pip.conf
check_command

# Step 3: Set Default Directory for Terminal Sessions
echo "Setting default directory for terminal sessions..."
echo "cd /usr/src/app" >> /home/airdroitech/.bashrc
source /home/airdroitech/.bashrc
check_command

# Step 4: Install Python Dependencies
echo "Installing required Python packages..."
sudo pip install mysql-connector-python hid fpdf segno esptool
check_command

echo "Duplicating the FactoryApp to ATSoftwareDevelopmentTool..."
cd /usr/src/app/

# Clone the FactoryApp repository to the new directory
git clone git@github.com:PolyaireDev/FactoryApp.git ATSoftwareDevelopmentTool
check_command

# Optionally remove the original FactoryApp if no longer needed
cd
rm -rf FactoryApp
check_command

# Step 5: Set Permissions on the result Folder
# Note: This part should be executed after the reboot
echo "Setting permissions on the result folder..."
chmod -R 777 /usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result
check_command
chmod g+s /usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result
check_command

cd /usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result
umask 000
touch test-file.txt
ls -l test-file.txt
rm test-file.txt
check_command

# Step 6: Run the Factory App (if required before rebooting)
echo "Running the Factory App..."
cd /usr/src/app/ATSoftwareDevelopmentTool
python3 main.py &
check_command

# Step 7: Update package list and install Samba server
echo "Updating package list..."
sudo apt update -y
check_command

echo "Installing Samba server..."
sudo apt install samba -y
check_command

# Step 8: Configure Samba shared folder
echo "Configuring Samba shared folder..."
SHARED_FOLDER_PATH="/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result"
SAMBA_CONF="/etc/samba/smb.conf"
SAMBA_USER="airdroitech"

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
check_command

# Step 9: Restart Samba server
echo "Restarting Samba server..."
sudo systemctl restart smbd
check_command

# Step 10: Add Samba user
echo "Adding Samba user..."
sudo smbpasswd -a $SAMBA_USER
check_command

# Step 11: Enable I2C in config.txt
CONFIG_FILE="/boot/config.txt"

# Check if I2C is already enabled
if grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE"; then
    echo "I2C is already enabled in $CONFIG_FILE."
else
    echo "Enabling I2C in $CONFIG_FILE..."
    echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG_FILE" > /dev/null
fi

# Load the i2c-dev module
if grep -q "^i2c-dev" /etc/modules; then
    echo "i2c-dev module is already loaded."
else
    echo "Loading i2c-dev module..."
    echo "i2c-dev" | sudo tee -a /etc/modules > /dev/null
fi

# Step 12: Add cron job to run update_ssid.sh at boot
echo "Adding cron job to run update_ssid.sh at boot..."
cron_job="@reboot python3 /usr/src/app/ATSoftwareDevelopmentTool/scripts/update_ssid.sh"
(crontab -l 2>/dev/null; echo "$cron_job") | sudo crontab -
check_command

# Step 13: Reboot the Raspberry Pi
echo "Rebooting the Raspberry Pi to apply changes..."
sudo reboot