#!/bin/bash
# Disable screen blanking
xset s off
xset s noblank
xset -dpms

# Hide the mouse cursor after a short delay
unclutter -idle 0.5 -root &

# Launch Chromium in kiosk mode
@chromium-browser --noerrdialogs --disable-infobars --kiosk $URL &
#/usr/bin/python3 /usr/src/app/ATSoftwareDevelopmentTool/main.py 
