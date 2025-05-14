#!/bin/bash

# Function to get SSID from hostapd.conf
get_ssid_from_hostapd() {
    ssid=$(grep -E '^ssid=' /etc/hostapd/hostapd.conf | sed 's/^ssid=//')
    echo "$ssid"
}

# Function to update the SSID in testscript.ini
update_testscript_ini() {
    ini_file_path="/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/testscript.ini"
    ssid="$1"

    # Use `crudini` tool to update INI files if available
    if command -v crudini >/dev/null 2>&1; then
        crudini --set "$ini_file_path" wifi_station wifi_station_inputssid_command "FF:1;$ssid"
        crudini --set "$ini_file_path" wifi_station wifi_station_rpi_ssid "$ssid"
    else
        echo "crudini command not found. Please install it or use Python for complex INI file edits."
        exit 1
    fi
}

# Main script execution
ssid=$(get_ssid_from_hostapd)
if [ -n "$ssid" ]; then
    update_testscript_ini "$ssid"
    echo "Updated SSID to $ssid in testscript.ini"
else
    echo "SSID not found in hostapd.conf"
fi
