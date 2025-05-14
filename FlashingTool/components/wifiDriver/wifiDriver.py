import subprocess
import re

def scan_wifi_networks(interface='wlan0', fallback_interface='wlp44s0'):
    try:
        # Run iwlist scan command and capture output
        scan_output = subprocess.check_output(['sudo', 'iwlist', interface, 'scan'], stderr=subprocess.STDOUT)
        scan_output = scan_output.decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"Error scanning WiFi networks on {interface}: {e}")
        if fallback_interface and interface != fallback_interface:
            print(f"Attempting to scan using fallback interface: {fallback_interface}")
            return scan_wifi_networks(fallback_interface, None)
        else:
            return []

    # Debug: Print the raw scan output
    # print("Raw scan output:")
    # print(scan_output)

    # Use regular expressions to extract SSID and signal level (RSSI)
    networks = []
    current_network = {}
    lines = scan_output.splitlines()
    for line in lines:
        if re.match(r'^\s*Cell', line):
            if current_network:
                networks.append(current_network)
                current_network = {}
        elif re.search(r'\s*Signal level=(-?\d+) dBm', line):
            # Extract signal level (RSSI)
            match = re.search(r'Signal level=(-?\d+) dBm', line)
            if match:
                current_network['Signal_Level'] = match.group(1) + ' dBm'
        elif re.search(r'\s*ESSID', line):
            # Extract SSID
            match = re.search(r'ESSID:"(.*)"', line)
            if match:
                current_network['SSID'] = match.group(1)

    # Append the last network found
    if current_network:
        networks.append(current_network)

    return networks

def run_iwconfig(interface='wlan0'):
    try:
        # Run iwconfig command and capture output
        iwconfig_output = subprocess.check_output(['iwconfig', interface], stderr=subprocess.STDOUT)
        iwconfig_output = iwconfig_output.decode('utf-8')
        
        # Debug: Print the raw iwconfig output
        print("Raw iwconfig output:")
        print(iwconfig_output)
        
        # Extract SSID and signal level using regex
        ssid = re.search(r'ESSID:"(.*)"', iwconfig_output)
        signal_level = re.search(r'Signal level=(-?\d+) dBm', iwconfig_output)
        
        return {
            'SSID': ssid.group(1) if ssid else 'Unknown',
            'Signal_Level': signal_level.group(1) + ' dBm' if signal_level else 'N/A',
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Error running iwconfig on {interface}: {e}")
        return {}

if __name__ == "__main__":
    wifi_networks = scan_wifi_networks()
    if wifi_networks:
        print("Available WiFi networks:")
        for network in wifi_networks:
            ssid = network.get('SSID', 'Unknown')
            signal_level = network.get('Signal_Level', 'N/A')
            # print(f"SSID: {ssid}, Signal Level: {signal_level}")
            if ssid == 'AT-MT:Y1CA00O6148F-405J10':
                print(f"Target network found: SSID: {ssid}, Signal Level: {signal_level}")
                signal_level = int(signal_level.split(' ')[0])
                if signal_level >= -30 and signal_level <= -110:
                    print(f"Signal level is usable. {signal_level}")
                else:
                    print(f"Signal level is not usable. {signal_level}")
    else:
        print("No WiFi networks found.")
