#!/bin/bash

# Unblock Wi-Fi
rfkill unblock wifi

# Restart services
sudo systemctl restart hostapd.service
sudo systemctl restart dnsmasq

# Source the ESP-IDF export script
source /usr/src/app/esp/esp-idf/export.sh

# Print a message to indicate the script has been sourced
echo "ESP-IDF environment has been set up."

# Install required Python packages if not already installed
for package in pyudev mysql-connector-python hid pillow fpdf segno; do
    if ! pip show "$package" > /dev/null 2>&1; then
        pip install "$package"
    else
        echo "$package is already installed."
    fi
done

# Run the main Python script
python3 main.py
