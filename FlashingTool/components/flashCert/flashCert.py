# flash_cert.py

import os
import subprocess
import configparser
import logging
import ast
import time
import io

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(__file__)

# openocd_esp_usb_jtag_cfg_path = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/openocd/esp_usb_jtag.cfg"
# openocd_esp32s3_builtin_cfg_path = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/openocd/esp32s3-builtin.cfg"
openocd_esp_usb_jtag_cfg_path = "/home/airdroitech/.espressif/tools/openocd-esp32/v0.12.0-esp32-20240318/openocd-esp32/share/openocd/scripts/interface/esp_usb_jtag.cfg"
openocd_esp32s3_builtin_cfg_path = "/home/airdroitech/.espressif/tools/openocd-esp32/v0.12.0-esp32-20240318/openocd-esp32/share/openocd/scripts/board/esp32s3-builtin.cfg"


used_cert_ids = set()  # Track used cert-ids
# used_cert_file = '/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/used_cert_ids.pkl'
used_cert_file = str(script_dir) + "/../../used_cert_ids.pkl" 
class FlashCert:
    def __init__(self, status_label):
        self.status_label = status_label
        self.log_capture_string = io.StringIO()
        self.ch = logging.StreamHandler(self.log_capture_string)
        self.ch.setLevel(logging.INFO)
        self.ch.setFormatter(logging.Formatter('%(message)s'))
        # Clean up previous handlers if any to avoid duplicate logs
        if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
            logger.addHandler(self.ch)
        self.seleceted_order_number = None
        
        with open(used_cert_file, 'r') as f:  # Python 3: open(..., 'rb')
            try:
                self.used_cert_ids = ast.literal_eval(f.read())
                # used_cert_ids = pickle.load(f)
                # print('have used cert')
                # print(self.used_cert_ids)
            except Exception :
                self.used_cert_ids = set()
                # print('no used cert')
        
    def get_cert_ids_for_order(self, orders, selected_order_no):
        cert_ids = [order['esp-secure-cert-partition'] for order in orders if order['order-no'] == selected_order_no]
        return cert_ids

    def get_qrcode_for_cert_id(self, cert_ids, selected_cert_id):
        qrcode = [cert_id['qrcode'] for cert_id in cert_ids if cert_id['esp-secure-cert-partition'] == selected_cert_id]
        return qrcode
    
    def get_manualcode_for_cert_id(self, cert_ids, selected_cert_id):
        manualcode = [cert_id['manualcode'] for cert_id in cert_ids if cert_id['esp-secure-cert-partition'] == selected_cert_id]
        return manualcode
    
    def get_flashing_esp32s3_cert_status(self):
        self.ch.flush()
        log_contents = self.log_capture_string.getvalue()
        if "Flashing ESP32S3 Cert Complete" in log_contents:
            logger.info("Flashing ESP32S3 Cert Completed")
            print("Flashing ESP32S3 Cert Completed")
            self.update_status_label("Completed", "green", ("Helvetica", 10, "bold"))
        else:
            logger.info("Flashing ESP32S3 Cert Completed")
            print("Flashing ESP32S3 Cert Completed")
            self.update_status_label("Failed", "red", ("Helvetica", 10, "bold"))

    def flash_certificate(self, 
                        use_esptool,
                        production_mode, 
                        selected_port, 
                        selected_baud, 
                        serialnumber_label, 
                        serialnumber, 
                        foldername, 
                        certID_label, 
                        uuid, 
                        macAddr_label, 
                        macAddr, 
                        securecert_addr, 
                        dataprovider_addr
                        ):
        
        print('----flash_certificate----')
        # cert_dir = '/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/certs/' + str(serialnumber) + '/espsecurecert/out/146d_1/' + str(uuid)
        cert_dir = str(script_dir) + "/../../certs/" + str(serialnumber) + "/espsecurecert/out/" + str(foldername) + "/" + str(uuid)
        # cert_file_path = os.path.join(cert_dir, cert_id)
        cert_file_path = cert_dir + '/' + str(uuid) + '_esp_secure_cert.bin'
        print(str(cert_file_path))

        # if cert_file_path in self.used_cert_ids:
        #     logger.debug(f"Cert ID {cert_id} has already been used.")
        #     print(f"Cert ID {cert_id} has already been used.")
        #     return False
        
        # print(self.used_cert_ids)
        # print(cert_file_path)

        # logger.debug(f"Cert file path: {cert_file_path}")
        
        # Check if the file exists
        if production_mode == "True":
            pass
        else:
            if not os.path.isfile(cert_file_path):
                logger.error(f"Certificate file {cert_file_path} does not exist.")
                print(f"Certificate file {cert_file_path} does not exist.")
                return False

        # Replace _esp_secure_cert.bin with -partition.bin
        # part_bin_id = cert_id.replace('_esp_secure_cert.bin', '-partition.bin')
        # part_bin_path = os.path.join(cert_dir, part_bin_id)
        # logger.debug(f"Part bin file path: {part_bin_path}")
        part_bin_path = cert_dir + '/' + str(uuid) + '-partition.bin'
        print(str(part_bin_path))
        
        if not os.path.isfile(part_bin_path):
            logger.error(f"Partition bin file {part_bin_path} does not exist.")
            print(f"Partition bin file {part_bin_path} does not exist.")
            return False

        if cert_file_path:
            logger.debug(f"Cert file path: {cert_file_path}")
            if selected_port:
                logger.info(f"Flashing certificate with cert-id: {cert_file_path} on port {selected_port}")
                try:
                    logger.debug(f"ESP Secure Cert {cert_file_path} on port {selected_port}...")
                    print(f"ESP Secure Cert {cert_file_path} on port {selected_port}...")

                    self.certify(use_esptool, 
                                production_mode,
                                selected_port, 
                                selected_baud, 
                                cert_file_path, 
                                part_bin_path, 
                                securecert_addr, 
                                dataprovider_addr
                                )
                    
                    logger.info(f"FlashCert, Create New/Updata Database Start")
                    print(f"FlashCert, Create New/Updata Database Start")
                    print(f"ESP Secure Cert {cert_file_path} on port {selected_port}...")
                    self.update_status(serialnumber_label, serialnumber, certID_label, cert_file_path, macAddr_label, macAddr)
                    logger.info(f"FlashCert, Create New/Updata Database End")
                    print(f"FlashCert, Create New/Updata Database End")
                    # Uncomment if needed
                    # self.create_folder()
                    # self.save_cert_id_to_ini(os.path.join(os.path.dirname(__file__), self.get_serial_number()), cert_file_path)
                    # self.log_message(f"Cert {cert_file_path} flashed successfully.")
                    # self.update_status_label("Completed", "green", ("Helvetica", 10, "bold"))

                except Exception as e:
                    logger.error(f"Error during certification: {e}")
                    self.update_status_label("Failed", "red", ("Helvetica", 10, "bold"))
            else:
                logger.error("No port selected. Please select a port before flashing.")
                self.update_status_label("Failed", "red", ("Helvetica", 10, "bold"))
        else:
            logger.error(f"No .bin file found for certId {cert_file_path}.")
            self.update_status_label("Failed", "red", ("Helvetica", 10, "bold"))
            
        # Simulate flashing the certificate
        self.used_cert_ids.add(cert_file_path)
        with open(used_cert_file, 'w') as f: 
            f.write(str(self.used_cert_ids)) 
            #pickle.dump([used_cert_ids], f)
        return True

    def get_remaining_cert_ids(self, cert_ids):
        cert_dir = '/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/certs'
        return [cert_file_path for cert_file_path in cert_ids if os.path.join(cert_dir, cert_file_path) not in self.used_cert_ids]
        
    def get_certId(self):
        try:
            with open('/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
            # with open('/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
                for line in file:
                    if 'Matter Cert ID:' in line and 'Status: None' in line:
                        certId = line.split('Matter Cert ID: ')[1].split(',')[0].strip()
                        return certId
                self.log_message("No certId found in the text file.")
                return None
        except IOError as e:
            self.log_message(f"Error reading cert info from file: {e}")
            return None

    def create_folder(self):
        sn = self.get_serial_number()
        if sn:
            directory = os.path.join(os.path.dirname(__file__), sn)
            if not os.path.exists(directory):
                os.makedirs(directory)
                self.log_message(f"Directory {directory} created.")
            else:
                self.log_message(f"Directory {directory} already exists.")
        else:
            self.log_message("No serial number found.")

    def save_cert_id_to_ini(self, directory, certId):
        config = configparser.ConfigParser()
        config['CERT'] = {'certId': certId}
        config['SN'] = {'serialNumber': self.get_serial_number()}
        with open(os.path.join(directory, 'cert_info.ini'), 'w') as configfile:
            config.write(configfile)
        self.log_message(f"CertId {certId} saved to {os.path.join(directory, 'cert_info.ini')}")

    def certify(self, 
                use_esptool, 
                production_mode,
                selected_port, 
                selected_baud, 
                esp_bin_path, 
                part_bin_path, 
                securecert_addr, 
                dataprovider_addr
                ):
        
        global openocd_esp_usb_jtag_cfg_path
        global openocd_esp32s3_builtin_cfg_path

        logger.debug(f"Certify Process: Flashing cert with bin_path: {esp_bin_path} and part_bin_path: {part_bin_path}")
        print(f"Certify Process: Flashing cert with bin_path: {esp_bin_path} and part_bin_path: {part_bin_path}")

        # Define the path to the esp-idf directory
        esp_idf_path = "/usr/src/app/esp/esp-idf"

        if use_esptool == "True":
            if production_mode == "True":
                command = f"esptool.py -p {selected_port} -b {selected_baud} --no-stub write_flash {dataprovider_addr} {part_bin_path}\n"
            else:
                # Remove invocation of esp-idf to reduce flashing time.
                command = f"esptool.py -p {selected_port} -b {selected_baud} --no-stub write_flash {securecert_addr} {esp_bin_path} {dataprovider_addr} {part_bin_path}\n"
                # command = f"source {esp_idf_path}/export.sh\nesptool.py -p {selected_port} -b {selected_baud} --no-stub write_flash {securecert_addr} {esp_bin_path} {dataprovider_addr} {part_bin_path}\n"
                # command = f"esptool.py -p {selected_port} -b {selected_baud} write_flash {securecert_addr} {esp_bin_path} {dataprovider_addr} {part_bin_path}\n"
        else:
            if production_mode == "True":
                command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset halt; program_esp {part_bin_path} {dataprovider_addr} verify exit'"
            else:
                command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'init; reset halt; program_esp {esp_bin_path} {securecert_addr}; program_esp {part_bin_path} {dataprovider_addr} verify exit'"
                # command = f"source {esp_idf_path}/export.sh\nopenocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'program_esp {esp_bin_path} {securecert_addr}; program_esp {part_bin_path} {dataprovider_addr} verify exit'"
                # command = f"openocd -f {openocd_esp_usb_jtag_cfg_path} -f {openocd_esp32s3_builtin_cfg_path} --command 'program_esp {esp_bin_path} {securecert_addr}; program_esp {part_bin_path} {dataprovider_addr} verify exit'"

        # command = (
        #     f"esptool.py --port {selected_port} write_flash 0x10000 {bin_path}"
        # )
        
        try:
            logger.info(f"Flashing ESP32S3 Cert with command: {command}")
            print(f"Flashing ESP32S3 Cert with command: {command}")
            # Open subprocess with stdout redirected to PIPE
            # process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            process = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Read stdout line by line and log in real-time
            for line in iter(process.stdout.readline, ''):
                logger.info("Flashing ESP32S3 Cert = " + line.strip())
                print("Flashing ESP32S3 Cert = " + line.strip())
                if f"{use_esptool}" == "True":
                    if "Hard resetting via RTS pin" in line:
                        logger.info("Flashing ESP32S3 Cert Complete")
                        print("Flashing ESP32S3 Cert Complete")
                        self.update_status_label("Completed", "green", ("Helvetica", 10, "bold"))
                    else:
                        pass
                else:
                    if "** Verify OK **" in line:
                        logger.info("Flashing ESP32S3 Cert Complete")
                        print("Flashing ESP32S3 Cert Complete")
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
        # self.get_flashing_esp32s3_cert_status()

    def update_status(self, serialId_label, serialId, cerId_label, certId_fullpath, macAddress_label, macAddress):
        logger.debug(f"Updating status for certId {certId_fullpath}")
        print(f"Updating status for certId {certId_fullpath}")
        # file_path = '/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt'
        # file_path = '/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt'
        file_path = str(script_dir) + "/../../device_data.txt" 

        # try:
        #     with open(file_path, 'r') as file:
        #         lines = file.readlines()
            
        #     with open(file_path, 'w') as file:
        #         for line in lines:
        #             if f'cert-id: {certId}' in line and 'Status: None' in line:
        #                 logger.debug(f"Updating status to '0' for certId {certId}")
        #                 line = line.replace('Status: None', 'Status: 0')
        #             file.write(line)
            
        #     self.log_message(f"Status updated to '0' for certId {certId} in cert_info.txt.")
        # logger.debug(f"Updating status for certId {certId}")
        # try:
        start_index = certId_fullpath.rfind('/') + 1  
        filtered_cert_id = certId_fullpath[start_index:]  # This includes the .bin extension

        logger.debug(f"Filtered certId = {cerId_label}: {filtered_cert_id}")
        print(f"Filtered certId = {cerId_label}: {filtered_cert_id}")
        logger.debug(f"Filtered macAddress = {macAddress_label}: {macAddress}")
        print(f"Filtered macAddress = {macAddress_label}: {macAddress}")
        
        try:
            with open(file_path, 'r') as file:
                logger.debug(f"Reading file: {file_path}")
                print(f"Reading file: {file_path}")
                lines = file.readlines()
                updated_lines = []
                for line in lines:
                    # print(f"Parent line --->{line}")
                    if f"{cerId_label}: {filtered_cert_id}" in line:
                        print(f"Old line --->{line}")
                        parts = line.split(',')
                        for i in range(len(parts)):
                            if parts[i] == f"{macAddress_label}: ":
                                print(f"Found --->{macAddress_label}: ")
                                parts[i] = f"{macAddress_label}: {macAddress}"
                                logger.info(f"Update to database = {macAddress_label}: {macAddress}")
                                print(f"Update to database = {macAddress_label}: {macAddress}")
                            elif parts[i] == f"{macAddress_label}: {macAddress}":
                                logger.info(f"Found in database = {macAddress_label}: {macAddress}")
                                print(f"Found in database = {macAddress_label}: {macAddress}")
                            else:
                                pass
                                # logger.info(f"Missing in database = {macAddress_label}: ")
                                # print(f"Missing in database = {macAddress_label}: ")
                        line = ','.join(parts)
                        print(f"New line --->{line}")
                    updated_lines.append(line)
            
            # Write the updated contents back to the file
            with open(file_path, 'w') as file:
                file.writelines(updated_lines)

            # with open(file_path, 'w') as file:
            #     logger.debug(f"Writing to file: {file_path}")
            #     print(f"Writing to file: {file_path}")
            #     for line in lines:
            #         # logger.debug(f"Reading line: {line}")
            #         if 'Status: 0' in line:
            #             # logger.debug("Status already updated.")
            #             # print("Status already updated.")
            #             # file.write(line)  # Writing unchanged line
            #             pass
            #         elif f'{cerId_label}: {filtered_cert_id}' in line:
            #             line_parts = line.split(',')
            #             for i, part in enumerate(line_parts):
            #                 if f'{macAddress_label}:' in part:
            #                     line_parts[i] = f" {macAddress_label}: {macAddress_label}"
            #                 else:
            #                     pass
            #                 updated_line = ','.join(line_parts)
            #                 updated_lines.append(updated_line)
            #             # logger.debug(f"Updating status to '0' for certId {filtered_cert_id}")
            #             # print(f"Updating status to '0' for certId {filtered_cert_id}")
            #             # line = line.rstrip() + ', Status: 0\n'
            #             # file.write(line)
            #         else:
            #             updated_lines.append(line)  # Writing unchanged line

            #         file.seek(0)
            #         file.writelines(updated_lines)
            #         file.truncate()
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            print(f"File not found: {file_path}")
        except IOError as e:
            logger.error(f"IO error occurred: {e}")
            print(f"File not found: {file_path}")
            
            # self.log_message(f"Status updated to '0' for certId {filtered_cert_id} in cert_info.txt.")
        # except IOError as e:
        #     self.log_message(f"Error updating status in file: {e}")
        # except Exception as e:
        #     self.log_message(f"An unexpected error occurred: {e}")

    # def flash_cert(self, port_var):
    #     certId = self.get_certId()
    #     selected_port = port_var
    #     if certId:
    #         bin_path = self.get_bin_path(certId)
    #         if bin_path:
    #             if selected_port:
    #                 self.log_message(f"Flashing cert {certId} on port {selected_port}...")
    #                 self.certify(bin_path, selected_port)
    #                 self.update_status(certId)
    #                 self.create_folder()
    #                 self.save_cert_id_to_ini(os.path.join(os.path.dirname(__file__), self.get_serial_number()), certId)
    #                 self.log_message(f"Cert {certId} flashed successfully.")
    #                 self.update_status_label("Completed", "green", ("Helvetica", 10, "bold"))
    #             else:
    #                 self.log_message("No port selected. Please select a port before flashing.")
    #                 self.update_status_label("Failed", "red", ("Helvetica", 10, "bold"))
    #         else:
    #             self.log_message(f"No .bin file found for certId {certId}.")
    #             self.update_status_label("Failed", "red", ("Helvetica", 10, "bold"))
    #     else:
    #         self.log_message("No available certId found in the text file.")
    #         self.update_status_label("Failed", "red", ("Helvetica", 10, "bold"))

    def get_bin_path(self, certId):
        for root, dirs, files in os.walk("/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/certs"):
        # for root, dirs, files in os.walk("/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/certs"):
            for file in files:
                if file.endswith(".bin") and certId in file:
                    return os.path.join(root, file)  # Return the path of the .bin file
        return None  # Return None if no .bin file with the certId is found

    def get_serial_number(self):
        return "DummySerialNumber"  # Replace with actual logic to retrieve serial number

    def log_message(self, message):
        logger.info(message)  # Replace this with your preferred logging mechanism
        # self.log_message_callback(message)

    def update_status_label(self, message, fg, font):
        self.status_label.config(text=message, fg=fg, font=font)  # Update the status label with the message


