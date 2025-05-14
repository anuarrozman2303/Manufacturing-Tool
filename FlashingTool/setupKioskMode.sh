#!/bin/bash

# Script to create non privilege user for kios mode
# Tested on Raspberry Pi OS 64bit

# Variables
USERNAME="kioskuser"
PASSWORD="aidroitech!"
URL="https://time.is/Kuala_Lumpur"

# Create the new user
adduser --gecos "" --disabled-password $USERNAME
echo "$USERNAME:$PASSWORD" | chpasswd

# Remove sudo privileges from the new user
deluser $USERNAME sudo

# Install necessary packages
# apt update
# apt install -y build-essential libudev-dev libusb-1.0-0-dev autoconf automake libtool \
#   gcc-aarch64-linux-gnu wget zlib1g-dev libssl-dev libncurses5-dev \
#   libncursesw5-dev libreadline-dev libsqlite3-dev \
#   libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev \
#   liblzma-dev tk-dev libffi-dev git mariadb-server default-libmysqlclient-dev \
#   python3-rpi.gpio unclutter

# pip install --break-system-packages pyserial \
#   pyinstaller mysql-connector-python requests hidapi pyhidapi esptool

# Configure automatic login for the new user
LIGHTDM_CONF="/etc/lightdm/lightdm.conf"

# Ensure the [Seat:*] section exists
if ! grep -q "^\[Seat:\*\]" $LIGHTDM_CONF; then
    echo "[Seat:*]" >> $LIGHTDM_CONF
fi

# Uncomment and/or update the autologin-user line
if grep -q "^#autologin-user=" $LIGHTDM_CONF; then
    sed -i "s/^#autologin-user=.*/autologin-user=$USERNAME/" $LIGHTDM_CONF
elif grep -q "^autologin-user=" $LIGHTDM_CONF; then
    sed -i "s/^autologin-user=.*/autologin-user=$USERNAME/" $LIGHTDM_CONF
else
    echo "autologin-user=$USERNAME" >> $LIGHTDM_CONF
fi

# Uncomment and/or update the autologin-user-timeout line
if grep -q "^#autologin-user-timeout=" $LIGHTDM_CONF; then
    sed -i "s/^#autologin-user-timeout=.*/autologin-user-timeout=0/" $LIGHTDM_CONF
elif grep -q "^autologin-user-timeout=" $LIGHTDM_CONF; then
    sed -i "s/^autologin-user-timeout=.*/autologin-user-timeout=0/" $LIGHTDM_CONF
else
    echo "autologin-user-timeout=0" >> $LIGHTDM_CONF
fi

# Create kiosk script
KIOSK_SCRIPT="/home/$USERNAME/kiosk.sh"
cat <<EOL > $KIOSK_SCRIPT
#!/bin/bash
# Disable screen blanking
xset s off
xset s noblank
xset -dpms

# Hide the mouse cursor after a short delay
unclutter -idle 0.5 -root &

# Launch Chromium in kiosk mode
# chromium-browser --noerrdialogs --disable-infobars --kiosk $URL &
/usr/bin/python3 /usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/main.py 

EOL

chmod +x $KIOSK_SCRIPT
chown $USERNAME:$USERNAME $KIOSK_SCRIPT

# Create autostart directory if it doesn't exist
AUTOSTART_DIR="/home/$USERNAME/.config/autostart"
mkdir -p $AUTOSTART_DIR
chown -R $USERNAME:$USERNAME /home/$USERNAME/.config

# Create autostart entry for the kiosk script
AUTOSTART_ENTRY="$AUTOSTART_DIR/kiosk.desktop"
cat <<EOL > $AUTOSTART_ENTRY
[Desktop Entry]
Type=Application
Name=Kiosk
Exec=$KIOSK_SCRIPT
EOL

chown $USERNAME:$USERNAME $AUTOSTART_ENTRY

# Reboot the system to apply changes
echo "Setup complete. Rebooting..."
reboot
