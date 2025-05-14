#!/bin/bash

# Script to Install and Setup XRDP on Raspberry Pi

# Function to update package list
update_packages() {
    echo "Updating package list..."
    sudo apt update
    echo "Package list updated."
}

# Function to install XRDP
install_xrdp() {
    echo "Installing XRDP..."
    sudo apt install -y xrdp
    echo "XRDP installation completed."
}

# Function to start and enable XRDP service
start_enable_xrdp() {
    echo "Enabling XRDP to start on boot..."
    sudo systemctl enable xrdp
    echo "Starting XRDP service..."
    sudo systemctl start xrdp
    echo "XRDP service started."
}

# Function to check XRDP status
check_xrdp_status() {
    echo "Checking XRDP status..."
    sudo systemctl status xrdp
}

# Main script execution
echo "Starting XRDP installation and setup..."

# Update packages
update_packages

# Install XRDP
install_xrdp

# Start and enable XRDP service
start_enable_xrdp

# Check XRDP status
check_xrdp_status

echo "XRDP setup completed. You can now connect to your Raspberry Pi remotely."
