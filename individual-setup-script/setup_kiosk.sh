#!/bin/bash

# Script to configure or disable kiosk mode for the existing user airdroitech

# Variables
USERNAME="airdroitech"
LIGHTDM_CONF="/etc/lightdm/lightdm.conf"
KIOSK_SCRIPT="/home/$USERNAME/kiosk.sh"
AUTOSTART_DIR="/home/$USERNAME/.config/autostart"
AUTOSTART_ENTRY="$AUTOSTART_DIR/kiosk.desktop"

# Required dependencies
REQUIRED_PACKAGES=(unclutter lxterminal)

# Function to check and install dependencies
check_and_install_dependencies() {
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! command -v $package &> /dev/null; then
            echo "Package $package is not installed. Installing..."
            sudo apt update && sudo apt install -y $package
            if [ $? -ne 0 ]; then
                echo "Error: Failed to install $package. Please install it manually."
                exit 1
            fi
        fi
    done
}

# Function to configure kiosk mode
configure_kiosk() {
    # Backup the LightDM configuration
    sudo cp $LIGHTDM_CONF $LIGHTDM_CONF.bak

    # Ensure the [Seat:*] section exists
    if ! grep -q "^\[Seat:\*\]" $LIGHTDM_CONF; then
        echo "[Seat:*]" | sudo tee -a $LIGHTDM_CONF
    fi

    # Set the autologin-user line
    if grep -q "^#autologin-user=" $LIGHTDM_CONF; then
        sudo sed -i "s/^#autologin-user=.*/autologin-user=$USERNAME/" $LIGHTDM_CONF
    elif grep -q "^autologin-user=" $LIGHTDM_CONF; then
        sudo sed -i "s/^autologin-user=.*/autologin-user=$USERNAME/" $LIGHTDM_CONF
    else
        echo "autologin-user=$USERNAME" | sudo tee -a $LIGHTDM_CONF
    fi

    # Set the autologin-user-timeout line
    if grep -q "^#autologin-user-timeout=" $LIGHTDM_CONF; then
        sudo sed -i "s/^#autologin-user-timeout=.*/autologin-user-timeout=0/" $LIGHTDM_CONF
    elif grep -q "^autologin-user-timeout=" $LIGHTDM_CONF; then
        sudo sed -i "s/^autologin-user-timeout=.*/autologin-user-timeout=0/" $LIGHTDM_CONF
    else
        echo "autologin-user-timeout=0" | sudo tee -a $LIGHTDM_CONF
    fi

    # Create kiosk script
    sudo bash -c "cat <<EOL > $KIOSK_SCRIPT
#!/bin/bash
# Disable screen blanking
xset s off
xset s noblank
xset -dpms

# Hide the mouse cursor after a short delay
unclutter -idle 0.5 -root &

# Launch your application in a terminal
lxterminal -e /usr/bin/python3 /usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/main.py
EOL"

    # Make the kiosk script executable
    sudo chmod +x $KIOSK_SCRIPT
    sudo chown $USERNAME:$USERNAME $KIOSK_SCRIPT

    # Create autostart directory if it doesn't exist
    sudo mkdir -p $AUTOSTART_DIR
    sudo chown -R $USERNAME:$USERNAME /home/$USERNAME/.config

    # Create autostart entry for the kiosk script
    sudo bash -c "cat <<EOL > $AUTOSTART_ENTRY
[Desktop Entry]
Type=Application
Name=Kiosk
Exec=$KIOSK_SCRIPT
EOL"

    # Change ownership of the autostart entry
    sudo chown $USERNAME:$USERNAME $AUTOSTART_ENTRY

    # Inform the user about the reboot
    echo "Setup complete. Rebooting..."
    sudo reboot
}

# Function to disable kiosk mode
disable_kiosk() {
    # Remove autologin-user settings
    sudo sed -i "/^autologin-user=$USERNAME/d" $LIGHTDM_CONF
    sudo sed -i "/^autologin-user-timeout=/d" $LIGHTDM_CONF

    # Remove kiosk script and autostart entry
    if [ -f $KIOSK_SCRIPT ]; then
        sudo rm $KIOSK_SCRIPT
    fi
    if [ -f $AUTOSTART_ENTRY ]; then
        sudo rm $AUTOSTART_ENTRY
    fi

    # Inform the user
    echo "Kiosk mode disabled. Please restart the system for changes to take effect."
}

# Main script logic
check_and_install_dependencies

if [ "$1" == "disable" ]; then
    disable_kiosk
else
    configure_kiosk
fi
