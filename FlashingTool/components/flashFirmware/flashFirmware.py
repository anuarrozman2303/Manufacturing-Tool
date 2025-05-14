import subprocess
import os
import logging
import signal
import io
import time
import re

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(__file__)

# openocd_esp_usb_jtag_cfg_path = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/openocd/esp_usb_jtag.cfg"
# openocd_esp32s3_builtin_cfg_path = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/openocd/esp32s3-builtin.cfg"
openocd_esp_usb_jtag_cfg_path = "/home/airdroitech/.espressif/tools/openocd-esp32/v0.12.0-esp32-20240318/openocd-esp32/share/openocd/scripts/interface/esp_usb_jtag.cfg"
openocd_esp32s3_builtin_cfg_path = "/home/airdroitech/.espressif/tools/openocd-esp32/v0.12.0-esp32-20240318/openocd-esp32/share/openocd/scripts/board/esp32s3-builtin.cfg"

esp32s3_mac_address = ""
esp32h2_mac_address = ""

class FlashFirmware:
    
    def __init__(self, status_label, status_label_1, status_label_2, status_label_3, status_label_4):
        self.status_label = status_label
        self.status_label_1 = status_label_1
        self.status_label_2 = status_label_2
        self.status_label_3 = status_label_3
        self.status_label_4 = status_label_4
        self.log_capture_string = io.StringIO()
        self.ch = logging.StreamHandler(self.log_capture_string)
        self.ch.setLevel(logging.INFO)
        self.ch.setFormatter(logging.Formatter('%(message)s'))
        # Clean up previous handlers if any to avoid duplicate logs
        if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
            logger.addHandler(self.ch)
    
    def find_bin_path(self, keyword, search_directory):
        for root, dirs, files in os.walk(search_directory):
            for file in files:
                if file.endswith(".bin") and keyword in file:
                    return os.path.join(root, file)
        return None
    
    def retrieve_esp32s3_mac_address(self):
        global esp32s3_mac_address
        return esp32s3_mac_address
    
    def retrieve_esp32h2_mac_address(self):
        global esp32h2_mac_address
        return esp32h2_mac_address
    
    def record_esp32s3_mac_address(self, mac_address):
        logger.info(f"ESP32S3 MAC Address: {mac_address}")
        self.get_esp32s3_mac_address_status()
    
    def export_esp_idf_path(self):
        print("--export_esp_idf_path--")
        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        # Define the command to source the export.sh script
        command = f"source {esp_idf_path}/export.sh"

        # Execute the command
        try:
            result = subprocess.run(command, shell=True, executable='/bin/bash', check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in result.stdout.splitlines():
                logger.info(line.strip())
                print(line.strip())
                if "idf.py build" in line:
                    logger.info("ESP-IDF environment variables set.")
                    return False
                else:
                    pass
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"An error occurred: {e}")
            return True

    def reset_openocd_device(self, port_var, baud_var):
        print("--reset_openocd_device--")
        global openocd_esp_usb_jtag_cfg_path
        global openocd_esp32s3_builtin_cfg_path
        selected_port = port_var
        selected_baud = baud_var

        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        # command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset run; shutdown'\n"
        command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset run; exit'\n"
        # command = f"openocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset run; exit'\n"

        try:
            logger.info(f"Reset ESP32S3: {command}")
            print(f"Reset ESP32S3: {command}")
            # Open subprocess with stdout redirected to PIPE
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                logger.info("Reset ESP32S3 = " + line.strip())
                print("Reset ESP32S3 = " + line.strip())
            #     if "** Verify OK **" in line:
            #         # process.send_signal(signal.SIGINT)
            #         logger.info("Firmware Flashing Complete")
            #         break

            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running openocd: {e}")

    def reset_esptool_device(self, device_name, port_var, baud_var):
        logger.info("--reset_esptool_device--")
        print("--reset_esptool_device--")
        global esp32s3_mac_address
        global esp32h2_mac_address
        selected_port = port_var
        selected_baud = baud_var
        
        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"
        
        # Remove invocation of esp-idf to reduce reset time
        # Change the reset command to read_mac because of the issue with the reset command cause by burning the eFuse
        command = f"esptool.py -p {selected_port} -b {selected_baud} --before default_reset --no-stub read_mac\n"
        # command = f"source {esp_idf_path}/export.sh\nesptool.py -p {selected_port} -b {selected_baud} run\n"
        
        try:
            # Open subprocess with stdout redirected to PIPE
            logger.info(f"Reset {device_name}: {command}")
            print(f"Reset {device_name}: {command}")
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                logger.info(f"Reset {device_name} = " + line.strip())
                print(f"Reset {device_name} = " + line.strip())

                # if "** Verify OK **" in line:
                #     # process.send_signal(signal.SIGINT)
                #     logger.info("Firmware Flashing Complete")
                #     break

                if f"{device_name}" == "ESP32S3":
                    if "MAC:" in line:
                        esp32s3_mac_address = line.split("MAC:")[1].strip()
                        esp32s3_mac_address = str(esp32s3_mac_address)
                        esp32s3_mac_address = esp32s3_mac_address.upper()
                        # self.update_status_label2(f"{esp32s3_mac_address}", "black", ("Helvetica", 10, "bold"))
                        # logger.info(f"{device_name} MAC Address: {esp32s3_mac_address}")
                        print(f"{device_name} MAC Address: {esp32s3_mac_address}")
                    else:
                        pass
                elif f"{device_name}" == "ESP32H2":
                    if "BASE MAC:" in line:
                        esp32h2_mac_address = line.split("BASE MAC:")[1].strip()
                        esp32h2_mac_address = str(esp32h2_mac_address)
                        esp32h2_mac_address = esp32h2_mac_address.upper()
                        # self.update_status_label3(f"{esp32h2_mac_address}", "black", ("Helvetica", 10, "bold"))
                        # logger.info(f"{device_name} MAC Address: {esp32h2_mac_address}")
                        print(f"{device_name} MAC Address: {esp32h2_mac_address}")
                    else:
                        pass
            
            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running esptool.py: {e}")

    def get_openocd_device_mac_address(self, port_var, baud_var):
        # logger.info("--get_openocd_device_mac_address--")
        print("--get_openocd_device_mac_address--")
        global openocd_esp_usb_jtag_cfg_path
        global openocd_esp32s3_builtin_cfg_path
        global esp32s3_mac_address
        selected_port = port_var
        selected_baud = baud_var

        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset halt; esp_get_mac; exit'\n"
        # command = f"openocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset halt; esp_get_mac; exit'\n"

        try:
            # logger.info(f"Get ESP32S3 MAC Address: {command}")
            print(f"Get ESP32S3 MAC Address: {command}")
            # Open subprocess with stdout redirected to PIPE
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                # logger.info(line.strip())
                print("Get ESP32S3 MAC Address = " + line.strip())
                if "esp_usb_jtag: serial" in line:
                    data = line.split('(')
                    # print(str(data[0]))
                    # print(str(data[1]))
                    mac_address = data[1]
                    esp32s3_mac_address = mac_address.replace(')','')
                    esp32s3_mac_address = str(esp32s3_mac_address.strip())
                    # print(esp32s3_mac_address)
                    self.update_status_label2(f"{esp32s3_mac_address}", "black", ("Helvetica", 10, "bold"))
                    # logger.info(f"ESP32S3 MAC Address: {esp32s3_mac_address}")
                    print(f"ESP32S3 MAC Address = {esp32s3_mac_address}")

            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")
            
        except subprocess.CalledProcessError as e:
            # logger.error(f"Error running openocd: {e}")
            print(f"Error running openocd: {e}")
            
    def espfuse_s3(self, port_var, fw_flag):
        # espefuse.py --do-not-confirm -p /dev/tty.usbserial-1140 burn_efuse SPI_BOOT_CRYPT_CNT 0x7
        logger.info("--espfuse_s3--")
        print("--espfuse_s3--")
        selected_port = port_var
        
        command = f"espefuse.py --do-not-confirm -p {selected_port} burn_efuse SPI_BOOT_CRYPT_CNT 0x7\n"
        
        try:
            logger.info(f"ESP32S3 eFuse: {command}")
            print(f"ESP32S3 eFuse: {command}")
            # Open subprocess with stdout redirected to PIPE
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                logger.info("ESP32S3 eFuse = " + line.strip())
                print("ESP32S3 eFuse = " + line.strip())
                if "SPI_BOOT_CRYPT_CNT is already burned" in line:
                    logger.info("ESP32S3 eFuse Already Burned")
                    print("ESP32S3 eFuse Already Burned")
                    self.update_status_label4("Failed", "red", ("Helvetica", 10, "bold"))
                    break
                else:
                    print("ESP32S3 eFuse Burned")
                    if "Successful" in line:
                        logger.info("ESP32S3 eFuse Complete")
                        print("ESP32S3 eFuse Complete")
                        self.update_status_label4("Completed", "green", ("Helvetica", 10, "bold"))
                    else:
                        if fw_flag == True:
                            self.update_status_label4("Completed", "green", ("Helvetica", 10, "bold"))
                        else:
                            self.update_status_label4("Failed", "red", ("Helvetica", 10, "bold"))
            
            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running openocd: {e}")


    def erase_flash_s3(self, use_esptool, not_encrypted, port_var, baud_var, start_addr, end_addr):
        logger.info("--erase_flash_s3_--")
        print("--erase_flash_s3_--")
        global openocd_esp_usb_jtag_cfg_path
        global openocd_esp32s3_builtin_cfg_path
        selected_port = port_var
        selected_baud = baud_var

        if f"{not_encrypted}" == "False":
            logger.info("Skip erase flash s3")
            print("Skip erase flash s3")
        else:
            # # Define keywords for each bin file
            # keywords = {
            #     "boot_loader": "bootloader",
            #     "partition_table": "partition-table",
            #     "ota_data_initial": "ota_data_initial",
            #     # "firmware": "adt_matter_project_"
            #     # "firmware": "v1_0_0-20240716-de5"
            #     "firmware": "v1_0_0-20240717-rc1"
            # }

            # Define the directory to search in
            # search_directory = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/firmware/s3"
            # search_directory = "/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/firmware/s3"
            search_directory = str(script_dir) + "/../../firmware/s3" 

            # # Find paths for each bin file using keywords
            # bin_paths = {key: self.find_bin_path(keyword, search_directory) for key, keyword in keywords.items()}

            # boot_loader_path = bin_paths["boot_loader"]
            # partition_table_path = bin_paths["partition_table"]
            # ota_data_initial_path = bin_paths["ota_data_initial"]
            # fw_path = bin_paths["firmware"]

            # # Check if all paths are valid
            # if not all(bin_paths.values()):
            #     logger.error("Error: Unable to find one or more bin files")
            #     return

            # # Run esptool.py command
            # command = f"esptool.py -p {selected_port} -b {selected_baud} write_flash 0x0 {boot_loader_path} 0xc000 {partition_table_path} 0x1e000 {ota_data_initial_path} 0x200000 {fw_path}"

            # try:
            #     # Open subprocess with stdout redirected to PIPE
            #     process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            #     # Read stdout line by line and log in real-time
            #     for line in iter(process.stdout.readline, ''):
            #         logger.info(line.strip())
            #         if "Hard resetting via RTS pin" in line:
            #             logger.info("Firmware Flashing Complete")
            #             break
                                    
            #     process.stdout.close()
            #     process.wait()  # Wait for the process to finish

            # except subprocess.CalledProcessError as e:
            #     logger.error(f"Error running esptool.py: {e}")
            # except Exception as e:
            #     logger.error(f"An unexpected error occurred: {e}")
            

            # Define the path to the esp-idf directory
            esp_idf_path = "/usr/src/app/esp/esp-idf"

            if f"{use_esptool}" == "True":
                # Remove invocation of esp-idf to reduce flashing time.
                # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} erase_flash\n"
                # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --no-stub erase_flash\n"
                command = f"esptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} erase_flash\n"
            else:
                command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset init; flash erase_address {start_addr} {end_addr}; exit'\n"
                # command = f"openocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset init; flash erase_address {start_addr} {end_addr}; shutdown'\n"

            try:
                logger.info(f"Erase Flash ESP32S3: {command}")
                print(f"Erase Flash ESP32S3: {command}")
                # Open subprocess with stdout redirected to PIPE
                process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

                # Read stdout line by line and log in real-time
                for line in iter(process.stdout.readline, ''):
                    logger.info("Erase Flash ESP32S3 = " + line.strip())
                    print("Erase Flash ESP32S3 = " + line.strip())
                    if f"{use_esptool}" == "True":
                        if "Chip erase completed successfully" in line:
                            logger.info("Erase Flash ESP32S3 Complete")
                            print("Erase Flash ESP32S3 Complete")
                        else:
                            pass
                    else:
                        if "PROF: Erased" in line:
                            logger.info("Erase Flash ESP32S3 Complete")
                            print("Erase Flash ESP32S3 Complete")
                        else:
                            pass

                # time.sleep(5)
                # Ensure the process has terminated
                print("Terminate subprocess")
                process.terminate()
                process.stdout.close()
                print("stdout close")
                process.wait()
                print("Wait Done")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Error running openocd: {e}")

    def flash_s3_firmware(self, use_esptool,
                        not_encrypted,
                        production_mode, 
                        port_var, 
                        baud_var, 
                        bootloader_addr, 
                        partition_table_addr, 
                        ota_data_initial_addr, 
                        fw_addr, 
                        fw_filename):
        
        logger.info("--flash_s3_firmware--")
        print("--flash_s3_firmware--")
        global openocd_esp_usb_jtag_cfg_path
        global openocd_esp32s3_builtin_cfg_path
        selected_port = port_var
        selected_baud = baud_var

        # Define keywords for each bin file
        keywords = {
            "boot_loader": "bootloader",
            "signed_boot_loader": "signed",
            "partition_table": "partition-table",
            "ota_data_initial": "ota_data_initial",
            # "firmware": "adt_matter_project_"
            # "firmware": "v1_0_0-20240716-de5"
            # "firmware": "v1_0_0-20240717-rc1"
            # "firmware": "v1_0_0-20240821-rc4"
            # "firmware": "v1_0_0-20240821-rc5"
            # "firmware": "v1_0_0-20240906-rc7"
            "firmware": f"{fw_filename}"

        }

        # Define the directory to search in
        # search_directory = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/firmware/s3"
        # search_directory = "/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/firmware/s3"
        search_directory = str(script_dir) + "/../../firmware/s3" 

        # Find paths for each bin file using keywords
        bin_paths = {key: self.find_bin_path(keyword, search_directory) for key, keyword in keywords.items()}

        boot_loader_path = bin_paths["boot_loader"]
        signed_boot_loader_path = bin_paths["signed_boot_loader"]
        partition_table_path = bin_paths["partition_table"]
        ota_data_initial_path = bin_paths["ota_data_initial"]
        fw_path = bin_paths["firmware"]
        
        print(f"boot_loader_path = {boot_loader_path}")
        print(f"signed_boot_loader_path = {signed_boot_loader_path}")

        # Check if all paths are valid
        if not all(bin_paths.values()):
            logger.error("Error: Unable to find one or more bin files")
            print("Error: Unable to find one or more bin files")
            return

        # # Run esptool.py command
        # command = f"esptool.py -p {selected_port} -b {selected_baud} write_flash 0x0 {boot_loader_path} 0xc000 {partition_table_path} 0x1e000 {ota_data_initial_path} 0x200000 {fw_path}"

        # try:
        #     # Open subprocess with stdout redirected to PIPE
        #     process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        #     # Read stdout line by line and log in real-time
        #     for line in iter(process.stdout.readline, ''):
        #         logger.info(line.strip())
        #         if "Hard resetting via RTS pin" in line:
        #             logger.info("Firmware Flashing Complete")
        #             break
                                
        #     process.stdout.close()
        #     process.wait()  # Wait for the process to finish

        # except subprocess.CalledProcessError as e:
        #     logger.error(f"Error running esptool.py: {e}")
        # except Exception as e:
        #     logger.error(f"An unexpected error occurred: {e}")
        

        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        if production_mode == True: 
            # Do not flash bootloader in production mode
            if f"{use_esptool}" == "True" and f"{not_encrypted}" == "True":
                # Remove invocation of esp-idf to reduce flashing time.
                # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --no-stub write_flash {bootloader_addr} {boot_loader_path} {partition_table_addr} {partition_table_path} {ota_data_initial_addr} {ota_data_initial_path} {fw_addr} {fw_path}\n"
                command = f"esptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --after hard_reset --no-stub write_flash {bootloader_addr} {boot_loader_path} {partition_table_addr} {partition_table_path} {ota_data_initial_addr} {ota_data_initial_path} {fw_addr} {fw_path}\n"

            elif f"{use_esptool}" == "True" and f"{not_encrypted}" == "False":
                # Remove invocation of esp-idf to reduce flashing time.
                # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --no-stub write_flash {bootloader_addr} {boot_loader_path} {partition_table_addr} {partition_table_path} {ota_data_initial_addr} {ota_data_initial_path} {fw_addr} {fw_path}\n"
                command = f"esptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --after hard_reset --no-stub write_flash --encrypt {bootloader_addr} {signed_boot_loader_path} {partition_table_addr} {partition_table_path} {ota_data_initial_addr} {ota_data_initial_path} {fw_addr} {fw_path} --force\n"
            else:
                command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset halt; program_esp {ota_data_initial_path} {ota_data_initial_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {boot_loader_path} {bootloader_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"
                # command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'program_esp {ota_data_initial_path} {ota_data_initial_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {boot_loader_path} {bootloader_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"
                # command = f"openocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'program_esp {ota_data_initial_path} {ota_data_initial_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {boot_loader_path} {bootloader_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"
                # command = f"openocd -s /home/anuarrozman/esp/openocd-esp32/share/openocd/scripts -f openocd/esp_usb_jtag.cfg -f openocd/esp32s3-builtin.cfg --command 'program {ota_data_initial_path} 0x1e000' --command 'program {partition_table_path} 0xc000' --command 'program {boot_loader_path} 0x0' --command 'program {fw_path} 0x200000' "
        else:
            if f"{use_esptool}" == "True" and f"{not_encrypted}" == "True":
                # Remove invocation of esp-idf to reduce flashing time.
                # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --no-stub write_flash {bootloader_addr} {boot_loader_path} {partition_table_addr} {partition_table_path} {ota_data_initial_addr} {ota_data_initial_path} {fw_addr} {fw_path}\n"
                command = f"esptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --after hard_reset --no-stub write_flash {bootloader_addr} {boot_loader_path} {partition_table_addr} {partition_table_path} {ota_data_initial_addr} {ota_data_initial_path} {fw_addr} {fw_path}\n"

            elif f"{use_esptool}" == "True" and f"{not_encrypted}" == "False":
                # Remove invocation of esp-idf to reduce flashing time.
                # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --no-stub write_flash {bootloader_addr} {boot_loader_path} {partition_table_addr} {partition_table_path} {ota_data_initial_addr} {ota_data_initial_path} {fw_addr} {fw_path}\n"
                command = f"esptool.py --chip esp32s3 -p {selected_port} -b {selected_baud} --after hard_reset --no-stub write_flash --encrypt {bootloader_addr} {signed_boot_loader_path} {partition_table_addr} {partition_table_path} {ota_data_initial_addr} {ota_data_initial_path} {fw_addr} {fw_path} --force\n"
            else:
                command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset halt; program_esp {ota_data_initial_path} {ota_data_initial_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {boot_loader_path} {bootloader_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"
                # command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'program_esp {ota_data_initial_path} {ota_data_initial_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {boot_loader_path} {bootloader_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"
                # command = f"openocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'program_esp {ota_data_initial_path} {ota_data_initial_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {boot_loader_path} {bootloader_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"
                # command = f"openocd -s /home/anuarrozman/esp/openocd-esp32/share/openocd/scripts -f openocd/esp_usb_jtag.cfg -f openocd/esp32s3-builtin.cfg --command 'program {ota_data_initial_path} 0x1e000' --command 'program {partition_table_path} 0xc000' --command 'program {boot_loader_path} 0x0' --command 'program {fw_path} 0x200000' "

        progress_pattern = re.compile(r"\((\d+)\s?%\)")
        
        try:
            logger.info(f"Flashing ESP32S3 Firmware: {command}")
            print(f"Flashing S3 Firmware: {command}")
            # Open subprocess with stdout redirected to PIPE
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                logger.info("Flashing ESP32S3 Firmware = " + line.strip())
                print("Flashing ESP32S3 Firmware = " + line.strip())
                
                match = progress_pattern.search(line)
                
                if f"{use_esptool}" == "True":
                    # print("match = " + str(match))
                    if match:
                        percentage = match.group(1)
                        # print(f"Percentage: {percentage}")
                        self.update_status_label(f"{percentage}%", "black", ("Helvetica", 10, "bold"))
                        
                    if "Hard resetting via RTS pin" in line:
                        logger.info("Flashing ESP32S3 Firmware Complete")
                        print("Flashing ESP32S3 Firmware Complete")
                        self.update_status_label("Completed", "green", ("Helvetica", 10, "bold"))
                    else:
                        pass
                else:
                    if "** Verify OK **" in line:
                        logger.info("Flashing ESP32S3 Firmware Complete")
                        print("Flashing ESP32S3 Firmware Complete")
                        self.update_status_label("Completed", "green", ("Helvetica", 10, "bold"))
                    else:
                        pass

            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running openocd: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        # After the process completes, update the flashing status
        # self.get_flashing_esp32s3_firmware_status()

    def erase_flash_h2(self, use_esptool, port_var, baud_var, start_addr, end_addr):
        global openocd_esp_usb_jtag_cfg_path
        global openocd_esp32s3_builtin_cfg_path
        selected_port = port_var
        selected_baud = baud_var

        # # Define keywords for each bin file
        # keywords = {
        #     "boot_loader": "bootloader",
        #     "partition_table": "partition-table",
        #     "firmware": "ATIR_H2.bin"
        # }

        # Define the directory to search in
        # search_directory = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/firmware/h2"
        # search_directory = "/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/firmware/h2"
        search_directory = str(script_dir) + "/../../firmware/h2" 

        # # Find paths for each bin file using keywords
        # bin_paths = {key: self.find_bin_path(keyword, search_directory) for key, keyword in keywords.items()}

        # boot_loader_path = bin_paths["boot_loader"]
        # partition_table_path = bin_paths["partition_table"]
        # fw_path = bin_paths["firmware"]

        # # Check if all paths are valid
        # if not all(bin_paths.values()):
        #     logger.error("Error: Unable to find one or more bin files")
        #     return

        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        if f"{use_esptool}" == "True":
            # Remove invocation of esp-idf to reduce erase flash time.
            # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32h2 -p {selected_port} -b {selected_baud} erase_flash\n"
            # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32h2 -p {selected_port} -b {selected_baud} --no-stub erase_flash\n"
            command = f"esptool.py --chip esp32h2 -p {selected_port} -b {selected_baud} erase_flash\n"
        else:
            command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset init; flash erase_address {start_addr} {end_addr}; exit'\n"
            # command = f"openocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset init; flash erase_address {start_addr} {end_addr}; shutdown'\n"

        try:
            logger.info(f"Erase Flash ESP32H2: {command}")
            print(f"Erase Flash ESP32H2: {command}")
            # Open subprocess with stdout redirected to PIPE
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                logger.info("Erase Flash ESP32H2 = " +line.strip())
                print("Erase Flash ESP32H2 = " +line.strip())
                if f"{use_esptool}" == "True":
                    if "Chip erase completed successfully" in line:
                        logger.info("Erase Flash ESP32H2 Complete")
                        print("Erase Flash ESP32H2 Complete")
                    else:
                        pass
                else:
                    if "PROF: Erased" in line:
                        logger.info("Erase Flash ESP32H2 Complete")
                        print("Erase Flash ESP32H2 Complete")
                    else:
                        pass

            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error running esptool.py: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
        
    def flash_h2_firmware(self, use_esptool, port_var, baud_var, bootloader_addr, partition_table_addr, fw_addr, fw_filename):
        global openocd_esp_usb_jtag_cfg_path
        global openocd_esp32s3_builtin_cfg_path
        selected_port = port_var
        selected_baud = baud_var

        # Define keywords for each bin file
        keywords = {
            "boot_loader": "bootloader",
            "partition_table": "partition-table",
            # "firmware": "ATIR_H2.bin"
            "firmware": f"{fw_filename}"
        }

        # Define the directory to search in
        # search_directory = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/firmware/h2"
        # search_directory = "/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/firmware/h2"
        search_directory = str(script_dir) + "/../../firmware/h2"

        # Find paths for each bin file using keywords
        bin_paths = {key: self.find_bin_path(keyword, search_directory) for key, keyword in keywords.items()}

        boot_loader_path = bin_paths["boot_loader"]
        partition_table_path = bin_paths["partition_table"]
        fw_path = bin_paths["firmware"]

        # Check if all paths are valid
        if not all(bin_paths.values()):
            logger.error("Error: Unable to find one or more bin files")
            print("Error: Unable to find one or more bin files")
            return

        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        if f"{use_esptool}" == "True":
            # Remove invocation of esp-idf to reduce flashing time.
            # command = f"source {esp_idf_path}/export.sh\nesptool.py --chip esp32h2 -p {selected_port} -b {selected_baud} --no-stub write_flash {bootloader_addr} {boot_loader_path} {partition_table_addr} {partition_table_path} {fw_addr} {fw_path}\n"
            command = f"esptool.py --chip esp32h2 -p {selected_port} -b {selected_baud} write_flash {bootloader_addr} {boot_loader_path} {partition_table_addr} {partition_table_path} {fw_addr} {fw_path}\n"
        else:
            command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset halt; program_esp {boot_loader_path} {bootloader_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"
            # command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'program_esp {boot_loader_path} {bootloader_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"
            # command = f"openocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'program_esp {boot_loader_path} {bootloader_addr}; program_esp {partition_table_path} {partition_table_addr}; program_esp {fw_path} {fw_addr} verify exit'\n"

        progress_pattern = re.compile(r"\((\d+)\s?%\)")

        try:
            logger.info(f"Flashing ESP32H2 Firmware: {command}")
            print(f"Flashing ESP32H2 Firmware: {command}")
            # Open subprocess with stdout redirected to PIPE
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                logger.info("Flashing ESP32H2 Firmware = " + line.strip())
                print("Flashing ESP32H2 Firmware = " + line.strip())
                if f"{use_esptool}" == "True":
                    
                    match = progress_pattern.search(line)
                    if match:
                        percentage = match.group(1)
                        # print(f"Percentage: {percentage}")
                        self.update_status_label1(f"{percentage}%", "black", ("Helvetica", 10, "bold"))
                    
                    if "Hard resetting via RTS pin" in line:
                        logger.info("Flashing ESP32H2 Firmware Complete")
                        print("Flashing ESP32H2 Firmware Complete")
                        self.update_status_label1("Completed", "green", ("Helvetica", 10, "bold"))
                    else:
                        pass
                else:
                    if "** Verify OK **" in line:
                        logger.info("Flashing ESP32H2 Firmware Complete")
                        print("Flashing ESP32H2 Firmware Complete")
                        self.update_status_label1("Completed", "green", ("Helvetica", 10, "bold"))
                    else:
                        pass

            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error running esptool.py: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
        
        # After the process completes, update the flashing status
        # self.get_flashing_esp32h2_firmware_status()

    def get_esp32s3_mac_address_status(self):
        self.ch.flush()
        log_contents = self.log_capture_string.getvalue()
        if "ESP32S3 MAC Address:" in log_contents:
            logger.info(f"Get ESP32S3 MAC Address Completed")
            print(f"Get ESP32S3 MAC Address Completed")
            # self.update_status_label2("Completed", "green", ("Helvetica", 10, "bold"))
            pass
        else:
            logger.warning(f"Get ESP32S3 MAC Address Failed")
            print(f"Get ESP32S3 MAC Address Failed")
            self.update_status_label2("Failed", "red", ("Helvetica", 10, "bold"))

    def get_esp32h2_mac_address_status(self):
        self.ch.flush()
        log_contents = self.log_capture_string.getvalue()
        if "ESP32H2 MAC Address:" in log_contents:
            logger.info(f"Get ESP32H2 MAC Address Completed")
            print(f"Get ESP32H2 MAC Address Completed")
            # self.update_status_label3("Completed", "green", ("Helvetica", 10, "bold"))
            pass
        else:
            logger.warning(f"Get ESP32H2 MAC Address Failed")
            print(f"Get ESP32H2 MAC Address Failed")
            self.update_status_label3("Failed", "red", ("Helvetica", 10, "bold"))

    def get_flashing_esp32s3_firmware_status(self):
        self.ch.flush()
        log_contents = self.log_capture_string.getvalue()
        if "Flashing ESP32S3 Firmware Complete" in log_contents:
            logger.info("Flashing ESP32S3 Firmware Completed")
            print("Flashing ESP32S3 Firmware Completed")
            self.update_status_label("Completed", "green", ("Helvetica", 10, "bold"))
        else:
            logger.warning("Flashing ESP32S3 Firmware Failed")
            print("Flashing ESP32S3 Firmware Failed")
            self.update_status_label("Failed", "red", ("Helvetica", 10, "bold"))
            
    def get_flashing_esp32h2_firmware_status(self):
        self.ch.flush()
        log_contents = self.log_capture_string.getvalue()
        if "Flashing ESP32H2 Firmware Complete" in log_contents:
            logger.info("Flashing ESP32H2 Firmware Completed")
            print("Flashing ESP32H2 Firmware Completed")
            self.update_status_label1("Completed", "green", ("Helvetica", 10, "bold"))
        else:
            logger.warning("Flashing ESP32H2 Firmware Failed")
            print("Flashing ESP32H2 Firmware Failed")
            self.update_status_label1("Failed", "red", ("Helvetica", 10, "bold"))
            
    def get_esptool_device_mac_address(self, device_name, port_var, baud_var):
        global esp32s3_mac_address
        global esp32h2_mac_address
        selected_port = port_var
        selected_baud = baud_var

        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        # Remove invocation of esp-idf to reduce read mac time.
        # command = f"source {esp_idf_path}/export.sh\nesptool.py -p {selected_port} -b {selected_baud} read_mac\n"
        command = f"esptool.py -p {selected_port} -b {selected_baud} read_mac\n"
        
        try:
            # Open subprocess with stdout redirected to PIPE
            # logger.info(f"Get {device_name} MAC Address: {command}")
            print(f"Get {device_name} MAC Address: {command}")
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                # logger.info(f"Get {device_name} MAC Address = " + line.strip())
                print(f"Get {device_name} MAC Address = " + line.strip())
                if f"{device_name}" == "ESP32S3":
                    if "MAC:" in line:
                        esp32s3_mac_address = line.split("MAC:")[1].strip()
                        esp32s3_mac_address = str(esp32s3_mac_address)
                        esp32s3_mac_address = esp32s3_mac_address.upper()
                        self.update_status_label2(f"{esp32s3_mac_address}", "black", ("Helvetica", 10, "bold"))
                        # logger.info(f"{device_name} MAC Address: {esp32s3_mac_address}")
                        print(f"{device_name} MAC Address: {esp32s3_mac_address}")
                    else:
                        pass
                elif f"{device_name}" == "ESP32H2":
                    if "BASE MAC:" in line:
                        esp32h2_mac_address = line.split("BASE MAC:")[1].strip()
                        esp32h2_mac_address = str(esp32h2_mac_address)
                        esp32h2_mac_address = esp32h2_mac_address.upper()
                        self.update_status_label3(f"{esp32h2_mac_address}", "black", ("Helvetica", 10, "bold"))
                        # logger.info(f"{device_name} MAC Address: {esp32h2_mac_address}")
                        print(f"{device_name} MAC Address: {esp32h2_mac_address}")
                    else:
                        pass
            
            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")
            
        except subprocess.CalledProcessError as e:
            # logger.error(f"Error running esptool.py: {e}")
            print(f"Error running esptool.py: {e}")

        time.sleep(1)
        # if f"{device_name}" == "ESP32S3":
        #     self.get_esp32s3_mac_address_status()
        # elif f"{device_name}" == "ESP32H2":
        #     self.get_esp32h2_mac_address_status()

    def get_esptool_device_model(self, port_var, baud_var):
        # global device_model_info
        selected_port = port_var
        selected_baud = baud_var

        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        # Remove invocation of esp-idf to reduce read device model time.
        # command = f"source {esp_idf_path}/export.sh\nesptool.py -p {selected_port} -b {selected_baud} read_mac\n"
        command = f"esptool.py -p {selected_port} -b {selected_baud} read_mac\n"
        
        device_model_info = ""
        
        try:
            # Open subprocess with stdout redirected to PIPE
            # logger.info(f"Get {port_var} model info command: {command}")
            print(f"Get {port_var} model info command: {command}")
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                # logger.info(f"Get {port_var} model info = " + line.strip())
                print(f"Get {port_var} model info = " + line.strip())
                if "Detecting chip type..." in line:
                    device_model_info = line.split("Detecting chip type...")[1].strip()
                    device_model_info = str(device_model_info)
                    device_model_info = device_model_info.upper()
                    # logger.info(f"{port_var} model info: {device_model_info}")
                    print(f"{port_var} model info: {device_model_info}")
                else:
                    pass
    
            # time.sleep(5)
            # Ensure the process has terminated
            print("Terminate subprocess")
            process.terminate()
            process.stdout.close()
            print("stdout close")
            process.wait()
            print("Wait Done")
            
        except subprocess.CalledProcessError as e:
            # logger.error(f"Error running esptool.py: {e}")
            print(f"Error running esptool.py: {e}")

        time.sleep(1)
        # if f"{device_name}" == "ESP32S3":
        #     self.get_esp32s3_mac_address_status()
        # elif f"{device_name}" == "ESP32H2":
        #     self.get_esp32h2_mac_address_status()

        return device_model_info

    def update_status_label(self, message, fg, font):
        self.status_label.config(text=message, fg=fg, font=font)  # Update the status label with the message
        
    def update_status_label1(self, message, fg, font):
        self.status_label_1.config(text=message, fg=fg, font=font)
        
    def update_status_label2(self, message, fg, font):
        self.status_label_2.config(text=message, fg=fg, font=font)

    def update_status_label3(self, message, fg, font):
        self.status_label_3.config(text=message, fg=fg, font=font)
        
    def update_status_label4(self, message, fg, font):
        self.status_label_4.config(text=message, fg=fg, font=font)


