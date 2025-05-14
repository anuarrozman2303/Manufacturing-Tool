#!/bin/bash

# Enable I2C in config.txt
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

# Reboot the system
echo "Rebooting the system to apply changes..."
sudo reboot
