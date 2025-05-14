 
#!/bin/bash
# Update package list and install necessary packages
echo "Updating package list and installing hostapd and dnsmasq..."
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq
# Stop services if they are running
echo "Stopping hostapd and dnsmasq services..."
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq
# Configure dhcpcd.conf to ignore wlan0
echo "Configuring dhcpcd.conf..."
echo "denyinterfaces wlan0" | sudo tee -a /etc/dhcpcd.conf
# Configure static IP address for wlan0
echo "Configuring /etc/network/interfaces..."
sudo tee /etc/network/interfaces <<EOF
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet dhcp
allow-hotplug wlan0
iface wlan0 inet static
    address 192.168.5.1
    netmask 255.255.255.0
    network 192.168.5.0
    broadcast 192.168.5.255
EOF
# Configure hostapd
echo "Creating hostapd configuration..."
sudo tee /etc/hostapd/hostapd.conf <<EOF
interface=wlan0
driver=nl80211
ssid=AirTouch_Pi_WiFi_A97417
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
ht_capab=[HT40][SHORT-GI-20][DSSS_CCK-40]
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
# Uncomment the following lines to enable password protection
#wpa=2
#wpa_key_mgmt=WPA-PSK
#wpa_passphrase=your_password_here
#rsn_pairwise=CCMP
EOF
echo "Updating hostapd default configuration..."
sudo sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd
# Backup existing dnsmasq configuration and create a new one
echo "Configuring dnsmasq..."
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
sudo tee /etc/dnsmasq.conf <<EOF
interface=wlan0
listen-address=192.168.5.1
bind-interfaces
server=8.8.8.8
domain-needed
bogus-priv
dhcp-range=192.168.5.100,192.168.5.200,24h
EOF
# Enable and start services
echo "Enabling and starting hostapd and dnsmasq services..."
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo systemctl start hostapd
sudo systemctl restart dnsmasq
# Reboot to apply changes
echo "Setup complete. Rebooting now..."
sudo reboot
 
 