import logging
import os

logger = logging.getLogger(__name__)
script_dir = os.path.dirname(__file__)

class WriteDeviceInfo:
    def __init__(self, send_command, status_label1, status_label2):
        self.send_command = send_command
        self.status_label1 = status_label1
        self.status_label2 = status_label2

    def send_entry_command(self, send_entry):
        command = send_entry.get() + "\r\n"
        self.send_command(command)
        send_entry.delete(0, "end")
        
    def send_serial_number_command(self):
        logger.debug(f"Product Name: ATBEAM")
        command = f"FF:3;PRD-ATBEAM\r\n"
        self.send_command(command)
        logger.info(f"Sent product name command: {command}")
        # self.update_status_in_text_file_serial_number(index, line) # Temporary bar this code Soo
        # self.status_label1.config(text="Success")
        # self.update_status_label1("Pass", "green", ("Helvetica", 12, "bold"))

    def get_serial_number_from_text_file(self):
        try:
            with open(str(script_dir) + "/../../device_data.txt", 'r') as file:
            # with open('/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
            # with open('/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
                lines = file.readlines()
                for index, line in enumerate(lines):
                    if 'serial-id:' in line and 'Status: 1' in line:
                        serial_number = line.split('serial-id:')[1].split(',')[0].strip()
                        return serial_number, index, line
                logger.error("No serial found with status 1 in the text file.")
                return None, None, None
        except IOError as e:
            logger.error(f"Error reading serial from file: {e}")
            return None, None, None

    def update_status_in_text_file_serial_number(self, index, old_line):
        try:
            with open(str(script_dir) + "/../../device_data.txt", 'r') as file:
            # with open('/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
            # with open('/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
                lines = file.readlines()

            lines[index] = old_line.replace('Status: 1', 'Status: 2')

            with open(str(script_dir) + "/../../device_data.txt", 'w') as file:
            # with open('/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'w') as file:
            # with open('/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'w') as file:
                file.writelines(lines)

            logger.info(f"Updated status of line {index + 1} to 2.")
        except IOError as e:
            logger.error(f"Error updating status in file: {e}")

    def send_serial_number_command(self, serial_number):
        # serial_number, index, line = self.get_serial_number_from_text_file() # Temporary bar this code Soo
        if serial_number:
            logger.debug(f"Serial number: {serial_number}")
            # command = f"FF:3;DID-{serial_number}\r\n"
            command = f"FF:3;SRN-{serial_number}\r\n"
            self.send_command(command)
            logger.info(f"Sent serial number command: {command}")
            # self.update_status_in_text_file_serial_number(index, line) # Temporary bar this code Soo
            # self.status_label1.config(text="Success")
            self.update_status_label1("Pass", "green", ("Helvetica", 12, "bold"))
        else:
            logger.error("Failed to send serial number command: Serial number not found")
            # self.status_label1.config(text="Failed")
            self.update_status_label1("Failed", "red", ("Helvetica", 12, "bold"))

    def get_mtqr_from_text_file(self):
        try:
            with open(str(script_dir) + "/../../device_data.txt", 'r') as file:
            # with open('/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
            # with open('/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
                lines = file.readlines()
                for index, line in enumerate(lines):
                    if 'qrcode:' in line and 'Status: 2' in line:
                        mtqr = line.split('qrcode:')[1].split(',')[0].strip()
                        return mtqr, index, line
                logger.error("No MTQR found with status 2 in the text file.")
                return None, None, None
        except IOError as e:
            logger.error(f"Error reading MTQR from file: {e}")
            return None, None, None

    def update_status_in_text_file_mtqr(self, index, old_line):
        try:
            with open(str(script_dir) + "/../../device_data.txt", 'r') as file:
            # with open('/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
            # with open('/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'r') as file:
                lines = file.readlines()

            lines[index] = old_line.replace('Status: 2', 'Status: 3')

            with open(str(script_dir) + "/../../device_data.txt", 'w') as file:
            # with open('/usr/src/app/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'w') as file:
            # with open('/home/anuarrozman/Airdroitech/ATSoftwareDevelopmentTool/FlashingTool/device_data.txt', 'w') as file:
                file.writelines(lines)

            logger.info(f"Updated status of line {index + 1} to 3.")
        except IOError as e:
            logger.error(f"Error updating status in file: {e}")

    def send_mtqr_command(self, mtqr):
        # mtqr, index, line = self.get_mtqr_from_text_file()
        if mtqr:
            logger.debug(f"Matter QR String: {mtqr}")
            command = f"FF:3;MTQR-{mtqr}\r\n"
            self.send_command(command)
            logger.info(f"Sent MTQR command: {command}")
            # self.update_status_in_text_file_mtqr(index, line) # Temporary bar this code Soo
            # self.status_label2.config(text="Success")
            self.update_status_label2("Pass", "green", ("Helvetica", 12, "bold"))
        else:
            logger.error("Failed to send MTQR command: MTQR not found")
            # self.status_label2.config(text="Failed")
            self.update_status_label2("Failed", "red", ("Helvetica", 12, "bold"))

    def update_status_label1(self, message, fg, font):
        self.status_label1.config(text=message, fg=fg, font=font)  # Update the status label with the message

    def update_status_label2(self, message, fg, font):
        self.status_label2.config(text=message, fg=fg, font=font)  # Update the status label with the message


# Assuming send_command is a function that sends a command to the device
def send_command(command):
    print(f"Sending command: {command}")
