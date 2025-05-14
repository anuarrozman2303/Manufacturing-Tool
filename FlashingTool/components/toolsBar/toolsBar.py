import subprocess
import requests
import logging
import mysql.connector
import os

logger = logging.getLogger(__name__)
script_dir = os.path.dirname(__file__)

class ToolsBar:
    def flash_tool_checking(self):
        command = "esptool.py --help"
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            output = result.stdout
            logger.debug("esptool.py is installed.")
            logger.debug(output)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running esptool.py: {e}")
            
    def download_list(self):
        url = "http://localhost:3000/devices"  # Correct endpoint
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad status codes
            data = response.json()

            self.create_table_if_not_exists()  # Ensure table exists before inserting data
            self.insert_data(data)
            self.write_to_text_file(data)
            self.display_data(data)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading data: {e}")
        except mysql.connector.Error as e:
            logger.error(f"Error with database operation: {e}")
    
    def create_table_if_not_exists(self):
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="anuarrozman2303",
                password="Matter2303!",
                database="device_mac_sn"
            )
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_info (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    matter_cert_id VARCHAR(255),
                    serial_number VARCHAR(255),
                    mac_address VARCHAR(255),
                    matter_qr_string VARCHAR(255),
                    status VARCHAR(255) DEFAULT NULL,
                    order_num INT
                )
            """)
            conn.commit()
            logger.debug("Ensured that the table device_info exists.")
        except mysql.connector.Error as e:
            logger.error(f"Error creating table: {e}")
        finally:
            cursor.close()
            conn.close()

    def insert_data(self, data):
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="anuarrozman2303",
                password="Matter2303!",
                database="device_mac_sn"
            )
            cursor = conn.cursor()
            for device in data:
                matter_cert_id = device.get("matter_cert_id", "N/A")
                serial_number = device.get("serial_no", "N/A")  # Correct key to access serial number
                mac_address = device.get("mac_address", "N/A")
                matter_qr_string = device.get("matter_qr_string", "N/A")
                status = device.get("status", "N/A")
                cursor.execute("INSERT INTO device_info (matter_cert_id, serial_number, mac_address, matter_qr_string, status) VALUES (%s, %s, %s, %s, %s)", (matter_cert_id, serial_number, mac_address, matter_qr_string, status))
            conn.commit()
            logger.info("Data inserted successfully into database!")
        except mysql.connector.Error as e:
            logger.error(f"Error inserting data into database: {e}")
        finally:
            cursor.close()
            conn.close()
            
    def write_to_text_file(self, data):
        # file_path = "/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt"
        # file_path = '/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt'
        file_path = str(script_dir) + "/../../device_data.txt"
        if not os.path.exists(file_path):
            with open(file_path, 'w') as file:
                logger.debug(f"Created new file: {file_path}")
        
        with open(file_path, 'a') as file:
            # for device in data:
            #     matter_cert_id = device.get("matter_cert_id", "N/A")
            #     serial_number = device.get("serial_no", "N/A")  # Correct key to access serial number
            #     mac_address = device.get("mac_address", "N/A")
            #     matter_qr_string = device.get("matter_qr_string", "N/A")
            #     status = device.get("status", "N/A")
            #     order_num = device.get("order_num", "N/A")
            #     file.write(f"Matter Cert ID: {matter_cert_id}, Serial: {serial_number}, MAC Address: {mac_address}, Matter QR String: {matter_qr_string}, Status: {status}, Order Number: {order_num}\n")

            for device in data:
                order_no = device.get("order-no", "N/A")
                mac_address = device.get("mac-address", "N/A")
                serial_id = device.get("serial-id", "N/A")
                cert_id = device.get("cert-id", "N/A")
                esp_secure_cert_partition = device.get("esp-secure-cert-partition", "N/A")
                commissionable_data_provider_partition = device.get("commissionable-data-provider-partition", "N/A")
                qrcode = device.get("qrcode", "N/A")
                manualcode = device.get("manualcode", "N/A")
                discriminator = device.get("discriminator", "N/A")
                passcode = device.get("passcode", "N/A")
                file.write(f"order-no: {order_no}, mac-address: {mac_address}, serial-id: {serial_id}, cert-id: {cert_id}, esp-secure-cert-partition: {esp_secure_cert_partition}, commissionable-data-provider-partition: {commissionable_data_provider_partition}, qrcode: {qrcode}, manualcode: {manualcode}, discriminator: {discriminator}, passcode: {passcode}\n")
                
        
        logger.info(f"Data written to {file_path} successfully!")
        
    def display_data(self, data):
        # for device in data:
        #     matter_cert_id = device.get("matter_cert_id", "N/A")
        #     serial_number = device.get("serial_number", "N/A")  # Correct field name
        #     matter_qr_string = device.get("matter_qr_string", "N/A")
        #     status = device.get("status", "N/A")
        #     order_num = device.get("order_num", "N/A")
        #     logger.info(f"Matter Cert ID: {matter_cert_id}, Serial: {serial_number}, Matter QR String: {matter_qr_string}, Status: {status}, Order Number: {order_num}")
        for device in data:
            order_no = device.get("order-no", "N/A")
            mac_address = device.get("mac-address", "N/A")
            serial_id = device.get("serial-id", "N/A")
            cert_id = device.get("cert-id", "N/A")
            esp_secure_cert_partition = device.get("esp-secure-cert-partition", "N/A")
            commissionable_data_provider_partition = device.get("commissionable-data-provider-partition", "N/A")
            qrcode = device.get("qrcode", "N/A")
            manualcode = device.get("manualcode", "N/A")
            discriminator = device.get("discriminator", "N/A")
            passcode = device.get("passcode", "N/A")
            logger.info(f"order-no: {order_no}, mac-address: {mac_address}, serial-id: {serial_id}, cert-id: {cert_id}, esp-secure-cert-partition: {esp_secure_cert_partition}, commissionable-data-provider-partition: {commissionable_data_provider_partition}, qrcode: {qrcode}, manualcode: {manualcode}, discriminator: {discriminator}, passcode: {passcode}")


        logger.info("Data downloaded successfully!")

