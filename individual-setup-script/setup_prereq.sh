#!/bin/bash

# Raspberry Pi 4 Setup Script

# Step 1: Setup Directory Ownership and Structure
echo "Setting up directory ownership and structure..."
sudo chown -R airdroitech:airdroitech /usr/src
mkdir -p /usr/src/app

# Step 2: Enable pip for Package Management
echo "Configuring pip for package management..."
echo "[global]" | sudo tee /etc/pip.conf
echo "break-system-packages=true" | sudo tee -a /etc/pip.conf

# Step 3: Set Default Directory for Terminal Sessions
echo "Setting default directory for terminal sessions..."
echo "cd /usr/src/app" >> /home/airdroitech/.bashrc
source /home/airdroitech/.bashrc

# Step 4: Install Python Dependencies
echo "Installing required Python packages..."
sudo pip install mysql-connector-python hid fpdf segno esptool

echo "Duplicating the FactoryApp to ATSoftwareDevelopmentTool..."
cd /usr/src/app/

# Clone the FactoryApp repository to the new directory
git clone git@github.com:PolyaireDev/FactoryApp.git ATSoftwareDevelopmentTool

# Optionally remove the original FactoryApp if no longer needed
cd
rm -rf FactoryApp

# Step 5: Set Permissions on the result Folder
echo "Setting permissions on the result folder..."
chmod -R 777 /usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result
chmod g+s /usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result

cd /usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result
umask 000
touch test-file.txt
ls -l test-file.txt
rm test-file.txt

# Step 6: Add Cron Job to Run Script at Boot
echo "Adding cron job to run update_ssid.sh at boot..."
cron_job="@reboot python3 /usr/src/app/ATSoftwareDevelopmentTool/scripts/update_ssid.sh"
(crontab -l 2>/dev/null; echo "$cron_job") | sudo crontab -

# Step 7: Reboot the Raspberry Pi
echo "Rebooting the Raspberry Pi..."
sudo reboot

# Step 8: Run the Factory App (Optional)
echo "Running the Factory App..."
cd /usr/src/app/ATSoftwareDevelopmentTool
python3 main.py