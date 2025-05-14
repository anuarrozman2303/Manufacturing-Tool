import re
import os
import subprocess

script_dir = os.path.dirname(__file__)

# Paths
# file_path = r"C:\Engineering\FactoryApp-main\FactoryApp-main\FlashingTool\device_data.txt"
# dir_path = r"C:\Engineering\FactoryApp-main\FactoryApp-main\FlashingTool\components\sendToPrinter\result"

# file_path = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt"
# dir_path = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/result"

file_path = str(script_dir) + "/../../device_data.txt" 
dir_path = str(script_dir) + "/result"
prg_path = str(script_dir) + "/main.py"

# Regex patterns
mac_address_pattern = re.compile(r'mac-address:\s*([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}')
manualcode_pattern = re.compile(r'manualcode:\s*([0-9-]+)')
qrcode_pattern = re.compile(r'qrcode:\s*MT:[^,]+')

# List of files in the result directory
files = os.listdir(dir_path)
files_string = ' '.join(files)

# Arrays
identified_manualcode_qrcode = []
to_print = []

def generate_polyaire_text_design(qrcode, manualcode):
    
    command = [
        # "python", "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/components/sendToPrinter/main.py",
        "python", f"{prg_path}",
        qrcode,
        manualcode,
        "1",
        "1"
    ]

    subprocess.call(command, env=os.environ)
    print(f"Printed [manualcode] = {manualcode} [qrcode] = {qrcode}")

# Code begin here 
try:
    with open(file_path, 'r') as file:
        for line in file:
            mac_match = mac_address_pattern.search(line)
            manualcode_match = manualcode_pattern.search(line)
            qrcode_match = qrcode_pattern.search(line)
            
            if mac_match and manualcode_match and qrcode_match:
                manualcode = manualcode_match.group(1).strip() 
                qrcode = qrcode_match.group(0).split(':', 1)[1].split(',')[0].strip()
                mac_address = mac_match.group(0).split(':', 1)[1].strip()
                
                identified_manualcode_qrcode.append([manualcode, qrcode])
                print(f"Identified [mac] = {mac_address} [manualcode] = {manualcode} [qrcode] = {qrcode}")

    for manual_code, qrcode in identified_manualcode_qrcode:
        prefix_pattern = re.escape(manual_code)
        if re.search(prefix_pattern, files_string):
            print(f"[manualcode] = {manual_code} exists - skipped")
        else:
            to_print.append([manual_code, qrcode])
            print(f"[manualcode] {manual_code} does not exist - added to printing queue")
    
    for manual_code, qrcode in to_print:
        generate_polyaire_text_design(qrcode, manual_code)

except Exception as e:
    print(f"An error occurred /components/sendToPrinter/schedulePrint.py: {e}")
