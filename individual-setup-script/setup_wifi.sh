#!/bin/bash

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

# Update package list and install necessary packages
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
# Uncomment the following lines to enable password protection
# wpa=2
# wpa_key_mgmt=WPA-PSK
# wpa_passphrase=your_password_here
# rsn_pairwise=CCMP
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

# Reboot to apply changes
echo "Setup complete. Rebooting now..."
sudo reboot
