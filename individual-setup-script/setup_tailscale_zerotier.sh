#!/bin/bash

# Script for Setting Up Tailscale and Zerotier on Raspberry Pi

# Function to install Tailscale
install_tailscale() {
    echo "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    echo "Tailscale installation completed."
}

# Function to join Tailscale network
join_tailscale_network() {
    echo "Joining Tailscale network..."
    sudo tailscale up
    echo "Joined Tailscale network. Checking status..."
    sudo tailscale status
    echo "Note down the Tailscale IP assigned to this device."
}

# Function to install Zerotier
install_zerotier() {
    echo "Installing Zerotier..."
    curl -s https://install.zerotier.com | sudo bash
    echo "Zerotier installation completed."
}

# Function to join Zerotier network
join_zerotier_network() {
    echo "Joining Zerotier network..."
    echo "Please enter your Zerotier network ID:"
    read NETWORK_ID
    sudo zerotier-cli join 272f5eae166d12a9
    echo "Zerotier join request sent. Please ensure the cloud admin approves it."
}

# Function to check Zerotier status
check_zerotier_status() {
    echo "Checking Zerotier status..."
    sudo zerotier-cli status
}

# Function to find and display IP addresses
display_ips() {
    echo "Finding assigned IP addresses..."
    echo "Tailscale IP:"
    sudo tailscale status | grep "Tailscale IP" || echo "Tailscale not connected"
    
    echo "Zerotier IP:"
    ifconfig | grep 'zt' || echo "Zerotier not connected"
}

# Main script execution
echo "Starting Tailscale and Zerotier setup..."

# Install Tailscale
install_tailscale
join_tailscale_network

# Install Zerotier
install_zerotier
join_zerotier_network
check_zerotier_status

# Display IP addresses
display_ips

echo "Setup completed. Please ensure you have noted down the Tailscale and Zerotier IPs."
echo "You can now connect from your Windows machine using SSH:"
echo "  ssh airdroitech@<Tailscale-IP>"
echo "  ssh airdroitech@<Zerotier-IP>"
