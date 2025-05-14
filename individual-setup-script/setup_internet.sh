#!/bin/bash

# Enable IP forwarding
echo "Enabling IP forwarding..."
sudo sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
sudo sysctl -p

# Set up NAT using iptables (replace 'eth0' with your internet interface if different)
echo "Setting up NAT using iptables..."
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"

# Ensure iptables rules persist on boot by adding to /etc/rc.local
echo "Ensuring iptables rules persist on boot..."
if ! grep -q "iptables-restore < /etc/iptables.ipv4.nat" /etc/rc.local; then
    sudo sed -i '$i\
    iptables-restore < /etc/iptables.ipv4.nat\
    ' /etc/rc.local
fi

# Restart network services to apply changes
echo "Restarting network services..."
sudo systemctl restart networking
sudo systemctl restart dnsmasq
sudo systemctl restart hostapd

echo "Internet sharing setup complete."
