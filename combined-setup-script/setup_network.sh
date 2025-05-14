#!/bin/bash

# Script for Setting Up Tailscale, Zerotier, Hostapd, Dnsmasq, XRDP, and Internet Sharing on Raspberry Pi

# Function to update package list
update_packages() {
    echo "Updating package list..."
    sudo apt update
    echo "Package list updated."
}

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
    sudo zerotier-cli join "$NETWORK_ID"
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

# Function to generate a random IP address in the 192.168.5.x range
generate_random_ip() {
    echo "192.168.5.$((RANDOM % 254 + 1))"
}

# Function to check the last command's success
check_command() {
    if [ $? -ne 0 ]; then
        echo "Error occurred. Exiting."
        exit 1
    fi
}

# Function to install Hostapd and Dnsmasq
install_hostapd_dnsmasq() {
    echo "Updating package list and installing hostapd and dnsmasq..."
    sudo apt-get update
    check_command
    sudo apt-get install -y hostapd dnsmasq
    check_command

    # Stop services if they are running
    echo "Stopping hostapd and dnsmasq services..."
    sudo systemctl stop hostapd
    check_command
    sudo systemctl stop dnsmasq
    check_command

    # Stop wpa_supplicant service if it is running
    echo "Stopping wpa_supplicant service if it is running..."
    sudo systemctl stop wpa_supplicant
    check_command

    # Configure dhcpcd.conf to ignore wlan0
    echo "Configuring dhcpcd.conf..."
    echo "denyinterfaces wlan0" | sudo tee -a /etc/dhcpcd.conf

    # Generate a random IP address for wlan0
    WLAN_IP=$(generate_random_ip)

    # Configure static IP address for wlan0
    echo "Configuring /etc/network/interfaces..."
    sudo tee /etc/network/interfaces <<EOF
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp

allow-hotplug wlan0
iface wlan0 inet static
    address $WLAN_IP
    netmask 255.255.255.0
    network 192.168.5.0
    broadcast 192.168.5.255
EOF

    # Extract the MAC address of wlan0
    MAC_ADDR=$(ip link show wlan0 | awk '/ether/ {print $2}')

    # Extract the last 6 digits of the MAC address
    LAST_6_DIGITS=$(echo "$MAC_ADDR" | sed 's/.*://g' | tail -c 7)

    # Create the SSID using the last 6 digits of the MAC address
    SSID="AirTouch_Pi_WiFi_${LAST_6_DIGITS}"

    # Configure hostapd
    echo "Creating hostapd configuration..."
    sudo tee /etc/hostapd/hostapd.conf <<EOF
interface=wlan0
driver=nl80211
ssid=$SSID
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
ht_capab=[HT40][SHORT-GI-20][DSSS_CCK-40]
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
EOF

    # Update hostapd default configuration
    echo "Updating hostapd default configuration..."
    sudo sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

    # Backup existing dnsmasq configuration and create a new one
    echo "Configuring dnsmasq..."
    sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
    sudo tee /etc/dnsmasq.conf <<EOF
interface=wlan0
bind-interfaces
server=8.8.8.8
domain-needed
bogus-priv
dhcp-range=192.168.5.100,192.168.5.200,24h
EOF

    # Verify IP Assignment to wlan0
    echo "Verifying IP assignment to wlan0..."
    if ! ip addr show wlan0 | grep -q "inet $WLAN_IP"; then
        echo "Assigning static IP address $WLAN_IP to wlan0..."
        sudo ifconfig wlan0 $WLAN_IP netmask 255.255.255.0 up
    fi

    # Enable and start services
    echo "Enabling and starting hostapd and dnsmasq services..."
    sudo systemctl unmask hostapd
    sudo systemctl enable hostapd
    sudo systemctl start hostapd
    check_command
    sudo systemctl enable dnsmasq
    sudo systemctl start dnsmasq
    check_command

    # Restart network services
    echo "Restarting network services..."
    sudo systemctl restart networking
    sudo systemctl restart dnsmasq

    # Verify that hostapd is running
    echo "Checking hostapd status..."
    sudo systemctl status hostapd

    # Setup /etc/rc.local for autostart on boot
    echo "Updating /etc/rc.local to ensure wlan0 is up on boot..."
    if ! grep -q "rfkill unblock wifi" /etc/rc.local; then
        sudo sed -i '$i\
rfkill unblock wifi\
ifconfig wlan0 up\
' /etc/rc.local
    fi
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

# Function to enable IP forwarding
enable_ip_forwarding() {
    echo "Enabling IP forwarding..."
    sudo sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
    sudo sysctl -p
}

# Function to set up NAT using iptables
setup_nat() {
    echo "Setting up NAT using iptables..."
    sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"
}

# Function to ensure iptables rules persist on boot
ensure_iptables_persist() {
    echo "Ensuring iptables rules persist on boot..."
    if ! grep -q "iptables-restore < /etc/iptables.ipv4.nat" /etc/rc.local; then
        sudo sed -i '$i\
iptables-restore < /etc/iptables.ipv4.nat\
' /etc/rc.local
    fi
}

# Function to restart network services to apply changes
restart_network_services() {
    echo "Restarting network services..."
    sudo systemctl restart networking
    sudo systemctl restart dnsmasq
    sudo systemctl restart hostapd
}

# Main script execution
echo "Starting setup of Tailscale, Zerotier, Hostapd, Dnsmasq, XRDP, and Internet Sharing..."

# Update packages
update_packages

# Install Tailscale
install_tailscale
join_tailscale_network

# Install Zerotier
install_zerotier
join_zerotier_network
check_zerotier_status

# Display IPs
display_ips

# Install Hostapd and Dnsmasq
install_hostapd_dnsmasq

# Install and configure XRDP
install_xrdp
start_enable_xrdp
check_xrdp_status

# Enable IP forwarding
enable_ip_forwarding

# Set up NAT
setup_nat

# Ensure iptables rules persist on boot
ensure_iptables_persist

# Restart network services
restart_network_services

echo "Setup complete."
