#git reset/revert happened on 2024 December 05, known stable commit hash is 2c3c188125c73abd58437bedecd157e881df939d

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.filedialog import askopenfilename
import serial.tools.list_ports
import os
from tkinter import messagebox
import configparser
import time
import threading
import logging
from pythonjsonlogger import jsonlogger
import subprocess
import argparse

import concurrent.futures
import http.client
import re
import json
import serial
import pyudev
from PIL import Image, ImageTk

from threading import Thread
from threading import Lock

from datetime import datetime
from components.settingWindow.settingWindow import SettingApp
from components.toolsBar.toolsBar import ToolsBar
from components.flashFirmware.flashFirmware import FlashFirmware
from components.flashCert.flashCert import FlashCert
from components.serialCom.serialCom import SerialCom
from components.writeDevInfo.writeDeviceInfo import WriteDeviceInfo
from components.dmmReader.multimeter import Multimeter
from components.dmmReader.dmmReader import DeviceSelectionApp
from components.manualTest.manualTest import ManualTestApp
from components.loadTestScript.loadTestScript import LoadTestScript
from components.aht20Sensor.aht20Sensor import SensorLogger
# from components.servoControl.servoControl import ServoController
from components.processOrderNumber.processOrderNumber import get_order_numbers
from components.readOrderFile.readOrderFile import parse_order_file
# from components.rebootPinS3.rebootPinS3 import RebootPinS3
from components.wifiDriver.wifiDriver import scan_wifi_networks
from components.sendToPrinter import sendToPrinterFunc

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(__file__)

factory_app_version = ""

formatted_date = ""
formatted_time = ""

logs_file_name = "factory_app"
logs_file_extension = ".log"
logs_dir_name = "logs"
logs_dir = str(script_dir) + "/" + str(logs_dir_name)

ini_file_name = "testscript.ini"

device_data_file_name = "device_data.txt"
device_data_file_path = str(script_dir) + "/" + str(device_data_file_name)

device_data = ""

orderNum_label = ""
macAddress_label = ""
serialID_label = ""
certID_label = ""
secureCertPartition_label = ""
commissionableDataPartition_label = ""
qrCode_label = ""
manualCode_label = ""
discriminator_label = ""
passcode_label = ""
rpi_mac_address_label = ""

orderNum_data = ""
macAddress_esp32s3_data = ""
serialID_data = ""
certID_data = ""
secureCertPartition_data = ""
commissionableDataPartition_data = ""
qrCode_data = ""
manualCode_data = ""
discriminator_data = ""
passcode_data = ""
rpi_mac_address_data = ""

orderNumber = ""
firmware_version_string = ""

available_com_ports = []

yes_no_button_handling_sequence = 0

check_esp32s3_module = 0

image_path = ""
disable_sticker_printing = 0

orders = parse_order_file(device_data_file_path)
order_numbers = get_order_numbers(orders)
qrcode = None
manualcode = None

break_printer = None

desired_width = 250
aspect_ratio = 1

retest_flag = 0
flash_only_flag = 0

sensor_txt_fullpath = str(script_dir) + "/sensor.txt"

master_start_time = ""

class SerialCommunicationApp:
    def __init__(self, root, debug_mode=False):
        # Load configuration from testscript.ini
        ini_file_path = os.path.join(script_dir, ini_file_name)

        config = configparser.ConfigParser()
        config.read(ini_file_path)

        # Get the debug_mode value from the configuration file
        debug_mode = config.getboolean('Settings', 'debugmode', fallback=False)
        print(f"Debug Mode: {debug_mode}")
        print(config.items('Settings'))

        self.root = root
        self.root.title("Serial Communication App")

        if debug_mode:
            self.root.attributes('-zoomed', True)  # Set window size for debug mode
        else:
            self.root.attributes('-fullscreen', True)  # Fullscreen mode

        self.root.resizable(True, True)

        # Serial port configuration
        self.serial_port = None
        self.task1_thread = None
        self.task2_thread = None
        self.task1_completed = threading.Event()
        self.task2_completed = threading.Event()
        self.task1_thread_failed = threading.Event()
        self.task2_thread_failed = threading.Event()
        self.stop_event = threading.Event()
        self.selected_port = ""
        self.step_delay = 3
        self.long_delay = 5
        self.manual_test = False
        self.factory_flag = None
        self.used_cert_ids = set()
        self.selected_cert_id = None
        self.cached_images = {}

        # Create GUI elements
        self.initialize_gui()

        # Initialize components
        self.initialize_components()

        self.manual_test_menu = None

        # time.sleep(5)

        self.refresh_dmm_devices()

    def initialize_logging(self, mac_address, serialID):
        global formatted_date
        global formatted_time

        if not mac_address:
            return True
        
        # Get the current date and time
        current_datetime = datetime.now()

        formatted_date = current_datetime.strftime("%Y%m%d")
        formatted_time = current_datetime.strftime("%H%M%S")

        # Configure logging
        # log_file_name = logs_dir + "/" + logs_file_name + '_' + str(mac_address) + '_' + str(serialID) + '_' + str(formatted_date) + '_' + str(formatted_time) + logs_file_extension
        # log_file_name = logs_dir + "/" + logs_file_name + '_' + str(serialID) + '_' + str(formatted_date) + '_' + str(formatted_time) + logs_file_extension
        log_file_name = logs_dir + "/" + str(formatted_date) + '_' + str(formatted_time) + '_' + logs_file_name + '_' + str(serialID) + logs_file_extension
        print(str(log_file_name))
        logging.basicConfig(
            force=True,
            filename=str(log_file_name),  # Name of the log file
            level=logging.DEBUG,  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        return False
    
    def initialize_gui(self):
        global factory_app_version
        self.create_menubar()
        self.create_widgets()
        # self.create_text_widgets()

        factory_app_version = self.read_version_from_file("version.txt")  # Read version from file
        self.add_version_label(factory_app_version)  # Add version number here
        print("initialize gui done")

    def initialize_components(self):

        self.toolsBar = ToolsBar()

        self.flashFw = FlashFirmware(self.result_flashing_fw_label,
                                    self.result_flashing_fw_h2_label,
                                    self.result_mac_address_s3_label, 
                                    self.result_mac_address_h2_label, 
                                    self.result_espfuse_s3) #(self.receive_text)
        
        self.flashCert = FlashCert(self.result_flashing_cert_label) #(self.log_message)
        
        self.initialize_serialCom(self.result_ir_def_label)

        # self.serialCom = SerialCom(self.result_factory_mode_label, #status_label
        #                             self.atbeam_temp_value, #status_label1
        #                             self.atbeam_humid_value, #status_label2
        #                             self.result_read_device_mac, #status_label3 
        #                             self.result_button_label, #status_label4
        #                             self.result_ir_def_label, #status_label5
        #                             self.result_read_prod_name, #status_label6
        #                             self.read_device_mac, #status_label7
        #                             self.read_prod_name, #status_label8
        #                             self.read_device_sn, #status_label9
        #                             self.read_device_mtqr, #status_label10
        #                             self.result_save_device_data_label, #status_label11
        #                             self.read_save_device_data_label, #status_label12
        #                             self.result_rgb_off_label, #status_label13
        #                             self.result_group2_factory_mode, #status_label14
        #                             self.result_factory_reset, #status_label15
        #                             self.result_group2_wifi_station_rssi, #status_label16
        #                             self.read_device_firmware_version, #status_label17
        #                             self.read_device_matter_dac_vid, #status_label18
        #                             self.read_device_matter_dac_pid, #status_label19
        #                             self.read_device_matter_vid, #status_label20
        #                             self.read_device_matter_pid,#status_label21
        #                             self.read_device_matter_discriminator, #status_label22
        #                             self.result_test_irrx, #status_label23
        #                             self.read_save_application_data_label, #status_label24
        #                             self.test_irrx #status_label25
        #                             ) #self.atbeam_sensor_temp_update) #(self.receive_text)

        self.sendEntry = WriteDeviceInfo(self.send_command, 
                                        self.result_write_serialnumber,
                                        self.result_write_mtqr
                                        ) #, self.log_message)
        
        self.dmmReader = DeviceSelectionApp(self.dmm_frame, 
                                            self.input_3_3V_dmm, 
                                            self.input_5V_dmm)

        self.multimeter = Multimeter()
        # self.rebootPin = RebootPinS3()
        self.aht20Sensor = SensorLogger()
        # self.servo_controller = ServoController()
        print("initialize components done")
        
    def initialize_serialCom(self, ir_def_label):
        self.serialCom = SerialCom(self.result_factory_mode_label, #status_label
                            self.atbeam_temp_value, #status_label1
                            self.atbeam_humid_value, #status_label2
                            self.result_read_device_mac, #status_label3 
                            self.result_button_label, #status_label4
                            # self.result_ir_def_label, #status_label5
                            ir_def_label, #status_label5
                            self.result_read_prod_name, #status_label6
                            self.read_device_mac, #status_label7
                            self.read_prod_name, #status_label8
                            self.read_device_sn, #status_label9
                            self.read_device_mtqr, #status_label10
                            self.result_save_device_data_label, #status_label11
                            self.read_save_device_data_label, #status_label12
                            self.result_rgb_off_label, #status_label13
                            self.result_group2_factory_mode, #status_label14
                            self.result_factory_reset, #status_label15
                            self.result_group2_wifi_station_rssi, #status_label16
                            self.read_device_firmware_version, #status_label17
                            self.read_device_matter_dac_vid, #status_label18
                            self.read_device_matter_dac_pid, #status_label19
                            self.read_device_matter_vid, #status_label20
                            self.read_device_matter_pid,#status_label21
                            self.read_device_matter_discriminator, #status_label22
                            self.result_test_irrx, #status_label23
                            self.read_save_application_data_label, #status_label24
                            self.test_irrx #status_label25
                            ) #self.atbeam_sensor_temp_update) #(self.receive_text)

    def read_temp_aht20(self):
        ext_sensor = self.aht20Sensor.read_temp_sensor()
        ext_sensor = ext_sensor.strip()
        array = ext_sensor.split(' ')
        ext_sensor = float(array[0])
        # ext_sensor = float(ext_sensor.split(' ')[0]) # this step to remove °C
        # ext_sensor = 25.0
        logger.info(f"External Raw Temperature: {ext_sensor}")
        print(f"External Raw Temperature: {ext_sensor}")
        self.ext_raw_temp_value.config(text=f"Ext Raw {ext_sensor} °C", fg="black", font=("Helvetica", 10, "normal"))

        callibrated_ext_sensor = (0.9568*ext_sensor)-5.4626
        raw_ext_sensor = ext_sensor
        ext_sensor = callibrated_ext_sensor

        logger.info(f"External Calibrated Temperature: {ext_sensor}")
        print(f"External Calibrated Temperature: {ext_sensor}")
        self.ext_temp_value.config(text=f"Ext {ext_sensor} °C", fg="black", font=("Helvetica", 10, "normal"))

        time.sleep(3)

        range = self.range_temp_value.cget("text")
        range = float(range.strip())
        logger.info(f"Temperature Range: {range}")
        print(f"Temperature Range: {range}")
        
        atbeam_temp = self.atbeam_temp_value.cget("text")
        atbeam_temp = atbeam_temp.split(' ')[0]
        logger.info(f"Temperature Device: {atbeam_temp}")
        print(f"Temperature Device: {atbeam_temp}")
        try:
            atbeam_temp = float(atbeam_temp)
        except Exception as e:
            logger.info(f"Temperature device invalid")
            print(f"Temperature device invalid")
            self.result_temp_label.config(text=f"Failed", fg="red", font=("Helvetica", 10, "bold"))
        else:
            logger.info(f"ATBeam Temperature: {atbeam_temp}")
            print(f"ATBeam Temperature: {atbeam_temp}")
    
            if abs(ext_sensor - atbeam_temp) <= float(range):
                logger.info(f"Temperature is within ±{range} range")
                print(f"Temperature is within ±{range} range")
                logger.debug(f"Checking Pass Temperature: {ext_sensor} - {atbeam_temp} = {abs(ext_sensor - atbeam_temp)}")
                print(f"Checking Pass Temperature: {ext_sensor} - {atbeam_temp} = {abs(ext_sensor - atbeam_temp)}")
                self.result_temp_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
            else:
                logger.info(f"Temperature is out of ±{range} range")
                print(f"Temperature is out of ±{range} range")
                logger.debug(f"Checking Fail Temperature: {ext_sensor} - {atbeam_temp} = {abs(ext_sensor - atbeam_temp)}")
                print(f"Checking Fail Temperature: {ext_sensor} - {atbeam_temp} = {abs(ext_sensor - atbeam_temp)}")
                self.result_temp_label.config(text=f"Failed", fg="red", font=("Helvetica", 10, "bold"))

    def get_atbeam_temp(self):
        command = "FF:3;sensorTemp?\r\n"
        self.send_command(command)

    def compare_temp(self, ext_sensor, atbeam_temp, test_temperature_range):
        global sensor_txt_fullpath
        try:
            # with open('sensor.txt', 'r') as file:
            with open(f"{sensor_txt_fullpath}", 'r') as file:
                for line in file:
                    if "ATBeam Temperature:" in line:
                        ext_sensor = float(ext_sensor)
                        atbeam_temp = line.split(":")[1].strip()
                        atbeam_temp = float(atbeam_temp)
                        logger.info(f"ATBeam Temperature: {atbeam_temp}")
                        # self.datadog_logging("info", f"ATBeam Temperature: {atbeam_temp}")
                        print(f"ATBeam Temperature: {atbeam_temp}")
                        logger.info(f"External Temperature: {ext_sensor}")
                        # self.datadog_logging("info", f"External Temperature: {ext_sensor}")
                        print(f"External Temperature: {ext_sensor}")
                        if ext_sensor == atbeam_temp:
                            logger.info("Temperature matches")
                            # self.datadog_logging("info", "Temperature matches")
                            print("Temperature matches")
                            self.result_temp_label.config(text=f"Pass", fg="green", font=("Helvetica", 10, "bold"))
                        if abs(ext_sensor - atbeam_temp) <= float(test_temperature_range):
                            logger.info(f"Temperature is within ±{test_temperature_range} range")
                            # self.datadog_logging("info", f"Temperature is within ±{test_temperature_range} range")
                            print(f"Temperature is within ±{test_temperature_range} range")
                            self.result_temp_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        else:
                            logger.info(f"Temperature is out of ±{test_temperature_range} range")
                            # self.datadog_logging("info", f"Temperature is out of ±{test_temperature_range} range")
                            print(f"Temperature is out of ±{test_temperature_range} range")
                            self.result_temp_label.config(text=f"Failed", fg="red", font=("Helvetica", 10, "bold"))
        except FileNotFoundError:
            logger.error("File not found")
            self.datadog_logging(
                "error", 
                {
                        "summary": "File Not Found Error"
                }
            )
            print("File not found")

    def read_humid_aht20(self):
        ext_sensor = self.aht20Sensor.read_humid_sensor()
        ext_sensor = ext_sensor.strip()
        array = ext_sensor.split(' ')
        ext_sensor = float(array[0])
        # ext_sensor = float(ext_sensor.split(' ')[0]) # this step to remove %
        # ext_sensor = 50.5
        logger.debug(f"External Raw Humidity: {ext_sensor}")
        # self.datadog_logging("info", f"External Humidity: {ext_sensor}")
        print(f"External Raw Humidity: {ext_sensor}")
        self.ext_raw_humid_value.config(text=f"Ext Raw {ext_sensor} %", fg="black", font=("Helvetica", 10, "normal"))

        callibrated_ext_sensor = (ext_sensor + 22)
        raw_ext_sensor = ext_sensor
        ext_sensor = callibrated_ext_sensor

        logger.debug(f"External Calibrated Humidity: {ext_sensor}")
        print(f"External Calibrated Humidity: {ext_sensor}")
        self.ext_humid_value.config(text=f"Ext {ext_sensor} %", fg="black", font=("Helvetica", 10, "normal"))

        time.sleep(3)

        range = self.range_humid_value.cget("text")
        range = float(range.strip())
        logger.info(f"Humidity Range: {range}")
        # self.datadog_logging("info", f"Humidity Range: {range}")
        print(f"Humidity Range: {range}")
        
        # atbeam_humid = self.serialCom.sensor_humid_variable
        atbeam_humid = self.atbeam_humid_value.cget("text")
        atbeam_humid = atbeam_humid.split(' ')[0]
        logger.info(f"Humidity Device: {atbeam_humid}")
        # self.datadog_logging("info", f"Humidity Device: {atbeam_humid}")
        print(f"Humidity Device: {atbeam_humid}")
        try:
            atbeam_humid = float(atbeam_humid)
        except Exception as e:
            logger.info(f"Humidity device is invalid")
            self.datadog_logging(
                "error", 
                {
                        "summary": "Humidity Device Invalid"
                }
            )
            print(f"Humidity device is invalid")
            self.result_humid_label.config(text=f"Failed", fg="red", font=("Helvetica", 10, "bold"))
        else:
            logger.info(f"ATBeam Humidity: {atbeam_humid}")
            # self.datadog_logging("info", f"ATBeam Humidity: {atbeam_humid}")
            print(f"ATBeam Humidity: {atbeam_humid}")

            # self.get_atbeam_humid()
            # time.sleep(1)
            
            if abs(ext_sensor - atbeam_humid) <= float(range): # humid range
                logger.info(f"Humidity is within ±{range} range")
                # self.datadog_logging("info", f"Humidity is within ±{range} range")
                print(f"Humidity is within ±{range} range")
                logger.debug(f"Checking Pass Humidity: {ext_sensor} - {atbeam_humid} = {abs(ext_sensor - atbeam_humid)}")
                # self.datadog_logging("info", f"Checking Pass Humidity: {ext_sensor} - {atbeam_humid} = {abs(ext_sensor - atbeam_humid)}")
                print(f"Checking Pass Humidity: {ext_sensor} - {atbeam_humid} = {abs(ext_sensor - atbeam_humid)}")
                self.result_humid_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
            else:
                logger.info(f"Humidity is out of ±{range} range")
                # self.datadog_logging("info", f"Humidity is out of ±{range} range")
                print(f"Humidity is out of ±{range} range")
                logger.debug(f"Checking Fail Humidity: {ext_sensor} - {atbeam_humid} = {abs(ext_sensor - atbeam_humid)}")
                # self.datadog_logging("info", f"Checking Fail Humidity: {ext_sensor} - {atbeam_humid} = {abs(ext_sensor - atbeam_humid)}")
                print(f"Checking Fail Humidity: {ext_sensor} - {atbeam_humid} = {abs(ext_sensor - atbeam_humid)}")
                self.result_humid_label.config(text=f"Failed", fg="red", font=("Helvetica", 10, "bold"))
            # self.compare_humid(ext_sensor, self.serialCom.sensor_humid_variable, float(range.strip()))
            # pass

    def get_atbeam_humid(self):
        command = "FF:3;sensorHumi?\r\n"
        self.send_command(command)

    def compare_humid(self, ext_sensor, atbeam_humid, test_humidity_range):
        global sensor_txt_fullpath
        try:
            # with open('sensor.txt', 'r') as file:
            with open(f"{sensor_txt_fullpath}", 'r') as file:
                for line in file:
                    if "ATBeam Humidity:" in line:
                        ext_sensor = float(ext_sensor)
                        atbeam_humid = line.split(":")[1].strip()
                        atbeam_humid = float(atbeam_humid)
                        logger.info(f"ATBeam Humidity: {atbeam_humid}")
                        # self.datadog_logging("info", f"ATBeam Humidity: {atbeam_humid}")
                        print(f"ATBeam Humidity: {atbeam_humid}")
                        logger.info(f"External Humidity: {ext_sensor}")
                        # self.datadog_logging("info", f"External Humidity: {ext_sensor}")
                        print(f"External Humidity: {ext_sensor}")
                        if ext_sensor == atbeam_humid:
                            logger.info("Humidity matches")
                            # self.datadog_logging("info", "Humidity matches")
                            print("Humidity matches")
                            self.result_humid_label.config(text=f"Pass", fg="green", font=("Helvetica", 10, "bold"))
                        elif abs(ext_sensor - atbeam_humid) <= float(test_humidity_range): # humid range
                            logger.info(f"Humidity is within ±{test_humidity_range} range")
                            # self.datadog_logging("info", f"Humidity is within ±{test_humidity_range} range")
                            print(f"Humidity is within ±{test_humidity_range} range")
                            self.result_humid_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        else:
                            logger.info(f"Humidity is out of ±{test_humidity_range} range")
                            # self.datadog_logging("error", f"Humidity is out of ±{test_humidity_range} range")
                            print(f"Humidity is out of ±{test_humidity_range} range")
                            self.result_humid_label.config(text=f"Failed", fg="red", font=("Helvetica", 10, "bold"))
        except FileNotFoundError:
            logger.error("File not found")
            self.datadog_logging(
                "error", 
                {
                        "summary": "File Not Found"
                }
            )
            print("File not found")

    def isfloat(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def dmm_reader_3_3V_value_manual(self, dmm_value):
        self.submit_3_3V_dmm.config(state=tk.DISABLED)
        dmm_manual_input = dmm_value.get()
        range_value_input = self.range_value_3_3V_dmm.cget("text")
        logger.debug(f"Manual 3.3V DMM Value: {dmm_manual_input}")
        # self.datadog_logging("info", f"Manual 3.3V DMM Value: {dmm_manual_input}")
        print(f"Manual 3.3V DMM Value: {dmm_manual_input}")
        logger.debug(f"Manual 3.3V Test Range Value: {range_value_input}")
        # self.datadog_logging("info", f"Manual 3.3V Test Range Value: {range_value_input}")
        print(f"Manual 3.3V Test Range Value: {range_value_input}")
        self.dmm_3_3V_reader.config(text=f"{dmm_manual_input} V", fg="black", font=("Helvetica", 10, "bold"))

        if dmm_manual_input.isdigit() or self.isfloat(dmm_manual_input):
            logger.info(f"'dmm_manual_input' is numeric")
            self.datadog_logging(
                "info", 
                {
                        "summary": "'dmm_manual_input' is numeric"
                }
            )
            print(f"'dmm_manual_input' is numeric")
            if (3.3 - float(range_value_input)) <= float(dmm_manual_input) <= (3.3 + float(range_value_input)):
                self.result_3_3v_test.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
            else:
                self.result_3_3v_test.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        else:
            logger.info(f"'dmm_manual_input' is not numeric")
            self.datadog_logging(
                "error", 
                {
                        "summary": "'dmm_manual_input' is not numeric"
                }
            )
            print(f"'dmm_manual_input' is not numeric")
            self.result_3_3v_test.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    def dmm_reader_5V_value_manual(self, dmm_value):
        self.submit_5V_dmm.config(state=tk.DISABLED)
        dmm_manual_input = dmm_value.get()
        range_value_input = self.range_value_5V_dmm.cget("text")
        logger.debug(f"Manual 5V DMM Value: {dmm_manual_input}")
        # self.datadog_logging("info", f"Manual 5V DMM Value: {dmm_manual_input}")
        print(f"Manual 5V DMM Value: {dmm_manual_input}")
        logger.debug(f"Manual 5V Test Range Value: {range_value_input}")
        # self.datadog_logging("info", f"Manual 5V Test Range Value: {range_value_input}")
        print(f"Manual 5V Test Range Value: {range_value_input}")
        self.dmm_5V_reader.config(text=f"{dmm_manual_input} V", fg="black", font=("Helvetica", 10, "bold"))

        if dmm_manual_input.isdigit() or self.isfloat(dmm_manual_input):
            logger.info(f"'dmm_manual_input' is numeric")
            self.datadog_logging(
                "info", 
                {
                        "summary": "'dmm_manual_input' is numeric"
                }
            )
            print(f"'dmm_manual_input' is numeric")
            if (5.0 - float(range_value_input)) <= float(dmm_manual_input) <= (5.0 + float(range_value_input)):
                self.result_5v_test.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
            else:
                self.result_5v_test.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                # here
            # self.datadog_logging(
            #     "info",
            #     {
                    
            # )
        else:
            logger.info(f"'dmm_manual_input' is not numeric")
            self.datadog_logging(
                "error", 
                {
                        "summary": "'dmm_manual_input' is not numeric"
                }
            )
            print(f"'dmm_manual_input' is not numeric")
            self.result_5v_test.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    # def wifi_scanning(self, test_range):
    #     global qrCode_data
    #     global disable_sticker_printing

    #     if qrCode_data != "":
    #         mtqr_wifi = self.read_device_mtqr.cget("text")
    #         mtqr_wifi_name = f"AT-{mtqr_wifi}"
    #         logger.info(f"Device Wi-Fi Soft AP Development: {mtqr_wifi_name}")
    #         print(f"Device Wi-Fi Soft AP Name 1: {mtqr_wifi_name}")
    #         device_wifi_softap_name1 = f"AT-{qrCode_data}" #This is the same name use above "mtqr_wifi_name"
    #         logger.info(f"Device Wi-Fi Soft AP Name 1: {device_wifi_softap_name1}")
    #         print(f"Device Wi-Fi Soft AP Name 1: {device_wifi_softap_name1}")
    #         string = str(qrCode_data)
    #         last_six_character = string[-6:]
    #         device_wifi_softap_name2 = f"AT BEAM {last_six_character}"
    #         logger.info(f"Device Wi-Fi Soft AP Name 2: {device_wifi_softap_name2}")
    #         print(f"Device Wi-Fi Soft AP Name 2: {device_wifi_softap_name2}")
    #         logger.info(f"Wi-Fi Soft AP RSSI Test Range: {test_range}")
    #         print(f"Wi-Fi Soft AP RSSI Test Range: {test_range}")
    #         wifi_networks = scan_wifi_networks()
    #         if wifi_networks:
    #             print("Available WiFi networks:")
    #             for network in wifi_networks:
    #                 ssid = network.get('SSID', 'Unknown')
    #                 signal_level = network.get('Signal_Level', 'N/A')
    #                 # print(f"SSID: {ssid}, Signal Level: {signal_level}")
    #                 if ssid == mtqr_wifi_name:
    #                     logger.info(f"Target network found: SSID: {ssid}, Signal Level: {signal_level}")
    #                     print(f"Target network found: SSID: {ssid}, Signal Level: {signal_level}")
    #                     self.result_group2_wifi_softap_ssid.config(text=f"{ssid}", fg="black", font=("Helvetica", 10, "bold"))
    #                     self.result_group2_wifi_softap_rssi.config(text=f"{signal_level} dBm", fg="black", font=("Helvetica", 10, "bold"))
    #                     try:
    #                         signal_level = int(signal_level.split(' ')[0]) # this step to remove 'dBm"
    #                     except Exception as e:
    #                         logger.info("Wi-Fi Soft AP Test: Failed")
    #                         print("Wi-Fi Soft AP Test: Failed")
    #                         self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #                         disable_sticker_printing = 1
    #                     else:
    #                         if signal_level >= int(test_range):
    #                             logger.info("Wi-Fi Soft AP Test: Pass")
    #                             print("Wi-Fi Soft AP Test: Pass")
    #                             self.result_group2_wifi_softap.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
    #                         else:
    #                             logger.info("Wi-Fi Soft AP Test: Failed")
    #                             print("Wi-Fi Soft AP Test: Failed")
    #                             self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #                             disable_sticker_printing = 1
    #                     break
    #                 elif ssid == device_wifi_softap_name1:
    #                     logger.info(f"Target network found: SSID: {ssid}, Signal Level: {signal_level}")
    #                     print(f"Target network found: SSID: {ssid}, Signal Level: {signal_level}")
    #                     self.result_group2_wifi_softap_ssid.config(text=f"{ssid}", fg="black", font=("Helvetica", 10, "bold"))
    #                     self.result_group2_wifi_softap_rssi.config(text=f"{signal_level} dBm", fg="black", font=("Helvetica", 10, "bold"))
    #                     try:    
    #                         signal_level = int(signal_level.split(' ')[0]) # this step to remove 'dBm"
    #                     except Exception as e:
    #                         logger.info("Wi-Fi Soft AP Test: Failed")
    #                         print("Wi-Fi Soft AP Test: Failed")
    #                         self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #                         disable_sticker_printing = 1
    #                     else:
    #                         if signal_level >= int(test_range):
    #                             logger.info("Wi-Fi Soft AP Test: Pass")
    #                             print("Wi-Fi Soft AP Test: Pass")
    #                             self.result_group2_wifi_softap.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
    #                         else:
    #                             logger.info("Wi-Fi Soft AP Test: Failed")
    #                             print("Wi-Fi Soft AP Test: Failed")
    #                             self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #                             disable_sticker_printing = 1
    #                     break
    #                 elif ssid == device_wifi_softap_name2:
    #                     logger.info(f"Target network found: SSID: {ssid}, Signal Level: {signal_level}")
    #                     print(f"Target network found: SSID: {ssid}, Signal Level: {signal_level}")
    #                     self.result_group2_wifi_softap_ssid.config(text=f"{ssid}", fg="black", font=("Helvetica", 10, "bold"))
    #                     self.result_group2_wifi_softap_rssi.config(text=f"{signal_level} dBm", fg="black", font=("Helvetica", 10, "bold"))
    #                     try:    
    #                         signal_level = int(signal_level.split(' ')[0]) # this step to remove 'dBm"
    #                     except Exception as e:
    #                         logger.info("Wi-Fi Soft AP Test: Failed")
    #                         print("Wi-Fi Soft AP Test: Failed")
    #                         self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #                         disable_sticker_printing = 1
    #                     else:
    #                         if signal_level >= int(test_range):
    #                             logger.info("Wi-Fi Soft AP Test: Pass")
    #                             print("Wi-Fi Soft AP Test: Pass")
    #                             self.result_group2_wifi_softap.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
    #                         else:
    #                             logger.info("Wi-Fi Soft AP Test: Failed")
    #                             print("Wi-Fi Soft AP Test: Failed")
    #                             self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #                             disable_sticker_printing = 1
    #                     break
    #         else:
    #             logger.info("No WiFi networks found.")
    #             print("No WiFi networks found.")
    #     else:
    #         logger.info("qrCode_data is empty")
    #         print("qrCode_data is empty")
    
    # Function: wifi_scanning
    # Date: 22/11/2024
    # Modified by: Anuar
    # Reason for Modification: Optimized logging for better readability and maintainability.
    def wifi_scanning(self, test_range):
        global qrCode_data
        global disable_sticker_printing

        test_start_time = ""
        end_time = ""
        duration = ""
        
        test_start_time = datetime.now()
        
        logger.info(f"Start Time: {test_start_time}")
        
        if not qrCode_data:
            logger.error("qrCode_data is empty")
            # self.datadog_logging("error", "qrCode_data is empty")
            self.datadog_logging(
                "error",
                {
                        "summary": "QR Code Data Empty"
                    }
            )
            print("qrCode_data is empty")
            return

        # Generate device Wi-Fi names
        mtqr_wifi = self.read_device_mtqr.cget("text")
        mtqr_wifi_name = f"AT-{mtqr_wifi}"
        device_wifi_softap_name1 = f"AT-{qrCode_data}"
        last_six_character = qrCode_data[-6:]
        device_wifi_softap_name2 = f"AT BEAM {last_six_character}"
        
        # Log initial details
        print(f"Device Wi-Fi Soft AP Details:\n  Development: {mtqr_wifi_name}\n  Name 1: {device_wifi_softap_name1}\n  Name 2: {device_wifi_softap_name2}\n  RSSI Test Range: {test_range}")
        
        # Scan Wi-Fi networks
        wifi_networks = scan_wifi_networks()
        if not wifi_networks:
            logger.error("No WiFi networks found.")
            # self.datadog_logging("error", "No WiFi networks found.")
            self.datadog_logging(
                "error",
                {
                        "summary": "No WiFi Networks Found"
                    }
            )
            print("No WiFi networks found.")
            return

        print("Available WiFi networks:")
        for network in wifi_networks:
            ssid = network.get('SSID', 'Unknown')
            signal_level = network.get('Signal_Level', 'N/A')
            print(f"SSID: {ssid}, Signal Level: {signal_level}")

            # Check if the SSID matches any target name
            if ssid in [mtqr_wifi_name, device_wifi_softap_name1, device_wifi_softap_name2]:
                logger.info(f"Target network found: SSID: {ssid}, Signal Level: {signal_level}")
                self.datadog_logging(
                    "info",
                    {
                            "summary": "Target Network Found"
                    }
                )

                self.result_group2_wifi_softap_ssid.config(text=f"{ssid}", fg="black", font=("Helvetica", 10, "bold"))
                self.result_group2_wifi_softap_rssi.config(text=f"{signal_level} dBm", fg="black", font=("Helvetica", 10, "bold"))

                try:
                    # Parse signal level and evaluate test range
                    signal_level_value = int(signal_level.split(' ')[0])  # Remove 'dBm'
                    test_result = "Pass" if signal_level_value >= int(test_range) else "Failed"
                    result_color = "green" if test_result == "Pass" else "red"

                    self.result_group2_wifi_softap.config(text=test_result, fg=result_color, font=("Helvetica", 10, "bold"))
                    logger.info(f"Wi-Fi Soft AP Test: {test_result}")

                    print(f"Wi-Fi Soft AP Test: {test_result}")

                    # Disable sticker printing on failure
                    if test_result == "Failed":
                        disable_sticker_printing = 1

                except ValueError:
                    logger.error(f"Failed to parse signal level: {signal_level}")

                    print(f"Failed to parse signal level: {signal_level}")
                    self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                    disable_sticker_printing = 1

                end_time = datetime.now()
                
                duration = end_time - test_start_time
                
                logger.info(f"End Time: {end_time}")
                
                logger.info(f"Duration: {duration}")

                # Log test results to Datadog
                self.datadog_logging(
                    "info" if test_result == "Pass" else "error",
                    {
                            "summary": "End: Wi-Fi Soft AP",
                            "item": "Wi-Fi Soft AP",
                            "start_time": str(test_start_time),
                            "end_time": str(end_time),
                            "duration": str(duration),
                            "details": {
                                "Action": "Wi-Fi Soft AP Test",
                                "WiFi Name": ssid,
                                "Signal Level": signal_level,
                                "Result": test_result
                            }
                    }
                )
                break
        else:
            logger.error("Target network not found in scanned Wi-Fi networks.")
            # self.datadog_logging("error", "Target network not found.")
            self.datadog_logging(
                "error",
                {
                        "summary": "Target Network Not Found",
                    }
            )
            print("Target network not found.")


    # def get_atbeam_rssi(self, test_range):
    #     global disable_sticker_printing

    #     logger.info(f"Wi-Fi Station RSSI Test Range: {test_range}")
    #     print(f"Wi-Fi Station RSSI Test Range: {test_range}")
    #     read_signal_level = self.result_group2_wifi_station_rssi.cget("text")
    #     try:
    #         read_signal_level = int(read_signal_level.split(' ')[0])
    #     except Exception as e:
    #         logger.info(f"Wi-Fi Station RSSI: Failed")
    #         print(f"Wi-Fi Station RSSI: Failed")
    #         self.result_group2_wifi_station.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #         disable_sticker_printing = 1
    #     else:
    #         if read_signal_level >= int(test_range):
    #             logger.info(f"Wi-Fi Station RSSI: Pass")
    #             print(f"Wi-Fi Station RSSI: Pass")
    #             self.result_group2_wifi_station.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
    #         elif read_signal_level == 0:
    #             logger.info(f"Wi-Fi Station RSSI: Failed")
    #             print(f"Wi-Fi Station RSSI: Failed")
    #             self.result_group2_wifi_station.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #             disable_sticker_printing = 1
    #         else:
    #             logger.info(f"Wi-Fi Station RSSI: Failed")
    #             print(f"Wi-Fi Station RSSI: Failed")
    #             self.result_group2_wifi_station.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #             disable_sticker_printing = 1
    
    # Function: get_atbeam_rssi
    # Date: 22/11/2024
    # Modified by: Anuar
    # Reason for Modification: Integrated datadog_logging for consistent and optimized logging.
    def get_atbeam_rssi(self, test_range):
        global disable_sticker_printing

        test_start_time = ""
        end_time = ""
        duration = ""
        
        test_start_time = datetime.now()
        
        logger.info(f"Start Time: {test_start_time}")
        
        print(f"Wi-Fi Station RSSI Test Range: {test_range} dBm")

        # Retrieve and attempt to parse the signal level from the UI.
        read_signal_level = self.result_group2_wifi_station_rssi.cget("text")
        try:
            read_signal_level_value = int(read_signal_level.split(' ')[0])  # Extract RSSI value, removing "dBm" if present.
            self.datadog_logging(
                "info",
                {
                        "summary": "Wi-Fi Station RSSI Value",
                        "details": {
                            "Signal Level": read_signal_level_value
                        }
                }
            )
        except ValueError as e:
            self.datadog_logging(
                "error",
                {
                        "summary": "Failed to parse value, Wi-Fi Station RSSI Value Parsing"
                }
            )
            print("Wi-Fi Station RSSI: Failed to parse value.")
            self.result_group2_wifi_station.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
            disable_sticker_printing = 1
            return

        # Evaluate RSSI against the test range.
        if read_signal_level_value >= int(test_range):
            # self.datadog_logging("info", "Wi-Fi Station RSSI Test,\n" f"Test passed. Signal level: {read_signal_level_value} dBm meets or exceeds range: {test_range} dBm")
            print("Wi-Fi Station RSSI: Pass")
            self.result_group2_wifi_station.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
        elif read_signal_level_value == 0:
            # self.datadog_logging("warning", "Wi-Fi Station RSSI Test,\n" f"Test failed. Signal level: 0 dBm indicates no signal.")
            print("Wi-Fi Station RSSI: Failed (No signal detected)")
            self.result_group2_wifi_station.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
            disable_sticker_printing = 1
        else:
            # self.datadog_logging("warning", "Wi-Fi Station RSSI Test,\n" f"Test failed. Signal level: {read_signal_level_value} dBm is below range: {test_range} dBm")
            print("Wi-Fi Station RSSI: Failed")
            self.result_group2_wifi_station.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
            disable_sticker_printing = 1
            
            
        end_time = datetime.now()
        
        duration = end_time - test_start_time
        
        logger.info(f"End Time: {end_time}")
        
        logger.info(f"Duration: {duration}")   
        
        print(f"Duration: End Time {end_time} - Start Time {test_start_time}, Duration: {duration}")
            
        self.datadog_logging(
            "info" if read_signal_level_value >= int(test_range) else "error",
            {
                    "summary": "End: Wi-Fi Station",
                    "item": "Wi-Fi Station",
                    "start_time": str(test_start_time),
                    "end_time": str(end_time),
                    "duration": str(duration),
                    "details": {
                        "Action": "Wi-Fi Station Test",
                        "Signal Level": read_signal_level_value,
                        "Test Range": test_range,
                        "Result": self.result_group2_wifi_station.cget('text')
                    }
            }
        )

    def refresh_dmm_devices(self):
        self.dmmReader.refresh_devices()
        
    def flash_tool_checking(self):
        self.toolsBar.flash_tool_checking()

    def reboot_s3(self, gpio_method, use_esptool, port_var, baud_var):
        if gpio_method == True:
            self.rebootPin.reboot_esp32()
            self.rebootPin.cleanup()
        else:
            if use_esptool == True:
                self.flashFw.reset_esptool_device("ESP32S3", port_var, baud_var)
            else:
                self.flashFw.reset_openocd_device(port_var, baud_var)

    def reboot_h2(self, use_esptool, port_var, baud_var):
        if use_esptool == True:
            self.flashFw.reset_esptool_device("ESP32H2", port_var, baud_var)
        else:
            self.flashFw.reset_openocd_device(port_var, baud_var)

    def read_s3_mac_address(self, port_var, baud_var):
        # self.flashFw.get_openocd_device_mac_address(port_var, baud_var)
        self.flashFw.get_esptool_device_mac_address("ESP32S3",port_var, baud_var)

    def read_h2_mac_address(self, port_var, baud_var):
        self.flashFw.get_esptool_device_mac_address("ESP32H2",port_var, baud_var)

    def read_device_model(self, port_var, baud_var):
        device_model = self.flashFw.get_esptool_device_model(port_var, baud_var)
        return device_model

    def record_s3_mac_address(self, mac_address):
        self.flashFw.record_esp32s3_mac_address(mac_address)

    def erase_flash_esp32s3(self, enable, use_esptool, esp32s3_not_encrypted, port_var, baud_var, start_addr, end_addr):
        if enable == "True":
            self.flashFw.erase_flash_s3(use_esptool, esp32s3_not_encrypted, port_var, baud_var, start_addr, end_addr)
            logger.info("Erase Flash ESP32S3: Enabled")
            print("Erase Flash ESP32S3: Enabled")
        else:
            logger.info("Erase Flash ESP32S3: Disabled")
            print("Erase Flash ESP32S3: Disabled")
            # pass

    def erase_flash_esp32h2(self, enable, use_esptool, port_var, baud_var, start_addr, end_addr):
        if enable == "True":
            self.flashFw.erase_flash_h2(use_esptool, port_var, baud_var, start_addr, end_addr)
            logger.info("Erase Flash ESP32H2: Enabled")
            print("Erase Flash ESP32H2: Enabled")
        else:
            logger.info("Erase Flash ESP32H2: Disabled")
            print("Erase Flash ESP32H2: Disabled")
            # pass
        
    def s3_espfuse(self, port_var, fw_flag):
        print('espfuse_s3-start')
        self.flashFw.espfuse_s3(port_var, fw_flag)
        print('espfuse_s3-end')

    def flash_s3_firmware(self, 
                        use_esptool,
                        esp32s3_not_encrypted, 
                        production_mode, 
                        port_var, 
                        baud_var, 
                        bootloader_addr, 
                        partition_table_addr, 
                        ota_data_initial_addr, 
                        fw_addr, 
                        fw_filename
                        ):
        
        print('flash_s3_firmware-start');

        self.flashFw.flash_s3_firmware(use_esptool,
                                    esp32s3_not_encrypted, 
                                    production_mode, 
                                    port_var, 
                                    baud_var, 
                                    bootloader_addr, 
                                    partition_table_addr, 
                                    ota_data_initial_addr, 
                                    fw_addr, 
                                    fw_filename
                                    )
        
        print('flash_s3_firmware-end')

    def flash_h2_firmware(self, 
                        use_esptool, 
                        port_var, 
                        baud_var, 
                        bootloader_addr, 
                        partition_table_addr, 
                        fw_addr, 
                        fw_filename
                        ):
        
        self.flashFw.flash_h2_firmware(use_esptool, 
                                    port_var, 
                                    baud_var, 
                                    bootloader_addr, 
                                    partition_table_addr, 
                                    fw_addr, 
                                    fw_filename
                                    )

    def flash_cert(self, port_var):
        # self.flashCert.flash_cert(self.port_var)
        self.flashCert.flash_cert(port_var)

    def open_serial_port(self):
        selected_port = self.port_var1.get()
        selected_baud = int(self.baud_var1.get())
        self.serialCom.open_serial_port(selected_port, selected_baud)

    def close_serial_port(self):
        self.serialCom.close_serial_port()

    def get_device_mac(self):
        command = "FF:3;MAC?\r\n"
        self.send_command(command)

    # Function: send_command
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def send_command(self, command):
        if self.serialCom.serial_port and self.serialCom.serial_port.is_open:
            self.serialCom.serial_port.write(command.encode())
            logger.debug(f"SerialCom, Sent: {command.strip()}")
            self.datadog_logging(
                "info",
                {
                        "summary": f"SerialCom: {command.strip()}"
                        }
            )
            print(f"SerialCom, Sent: {command.strip()}")
        else:
            logger.error("SerialCom, Port is not open. Please open the port before sending commands.")
            self.datadog_logging(
                "error",
                {
                        "summary": "Port is not open. Please open the port before sending commands."
                }
            )
            print("SerialCom, Port is not open. Please open the port before sending commands.")

    def send_serial_number(self, serial_number):
        self.sendEntry.send_serial_number_command(serial_number)

    def send_mqtr(self, mtqr):
        self.sendEntry.send_mtqr_command(mtqr)

    def create_menubar(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New")
        file_menu.add_command(label="Open")
        file_menu.add_command(label="Setting", command=self.config_setting)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit) #Commend this line to disable exit button
        menubar.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Check Flash Tool", command=self.flash_tool_checking)
        tools_menu.add_command(label="Upload Test Script", command=self.load_test_script)
        self.manual_test_menu = tools_menu.add_command(label="Manual Test", command=self.manual_test)
        tools_menu.entryconfig("Manual Test", state=tk.DISABLED)
        self.tools_menu = tools_menu
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About")
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def config_setting(self):
        SettingApp(tk.Toplevel(self.root))

    def manual_test(self):
        ManualTestApp(self.root, self.send_command).open_manual_test_window()
        
    def read_order_numbers(self, file_path):
        order_numbers = []
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    if 'order-no' in line:
                        order_number = line.split('order-no: ')[1].split(',')[0].strip()
                        if order_number not in order_numbers:
                            order_numbers.append(order_number)
        except Exception as e:
            print("Error at readOrderFile.py!")
            print(f"File is missing! - ' {file_path} ' ")
            messagebox.showerror("Error", f" ' {file_path} ' - Missing")

        return order_numbers

    def on_order_selected(self, event):
        selected_order = event.widget.get()
        cert_ids = self.flashCert.get_cert_ids_for_order(orders, selected_order)
        remaining_cert_ids = self.flashCert.get_remaining_cert_ids(cert_ids)

        if remaining_cert_ids:
            self.cert_id_dropdown['values'] = remaining_cert_ids
            self.cert_id_dropdown.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        else:
            self.cert_id_label.config(text="No Cert IDs available for this order.")
            self.cert_id_dropdown.pack_forget()

        logger.info(f"Selected order: {selected_order}")
        self.datadog_logging(
            "info",
            {
                    "summary": f"Selected order, {selected_order}"
            }
        )

    def read_port_from_config(self):
        global ini_file_name
        global script_dir

        # Check in the specified directory
        ini_file_path = os.path.join(script_dir, ini_file_name)

        config = configparser.ConfigParser()
        config.read(ini_file_path)
        return config.get('flash', 'port', fallback=None)

    def flashCertificate(self, 
                        use_esptool,
                        production_mode, 
                        selected_port, 
                        selected_baud, 
                        serialID_label, 
                        serialID, 
                        foldername, 
                        certID_label, 
                        uuid, 
                        macAddr_label, 
                        macAddr, 
                        securecert_addr, 
                        dataprovider_addr
                        ):
        
        self.flashCert.flash_certificate(use_esptool,
                                        production_mode,
                                        selected_port, 
                                        selected_baud, 
                                        serialID_label, 
                                        serialID, 
                                        foldername, 
                                        certID_label, 
                                        uuid, 
                                        macAddr_label, 
                                        macAddr, 
                                        securecert_addr, 
                                        dataprovider_addr
                                        )

    def on_select_cert_id(self, event):
        global qrcode
        global manualcode
        # Retrieve the selected certificate ID from the dropdown
        selected_cert_id = event.widget.get()

        if selected_cert_id:
            # Store the selected certificate ID in an instance variable
            self.selected_cert_id = selected_cert_id

            # Update status label
            self.cert_status_label.config(text=f"Cert {selected_cert_id} selected.")
            qrcode = self.flashCert.get_qrcode_for_cert_id(orders, selected_cert_id)
            qrcode = str(qrcode).strip("[]'")
            manualcode = self.flashCert.get_manualcode_for_cert_id(orders, selected_cert_id)
            manualcode = str(manualcode).strip("[]'")
        else:
            # If no certificate ID is selected
            self.cert_status_label.config(text="No certificate selected.")


    def disable_frame(self, frame):
        for child in frame.winfo_children():
            child.configure(state='disabled')

    def enable_frame(self, frame):
        for child in frame.winfo_children():
            child.configure(state='normal')

    # Function: cancel_to_printer
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def cancel_to_printer(self):
        global break_printer

        logger.info(f"Print Sticker: Cancel")
        print(f"Print Sticker: Cancel")
        self.printer_status_data_label.config(text="Cancel", fg="red", font=("Helvetica", 10, "bold"))
        break_printer = 1
        self.datadog_logging(
            "error",
            {
                    "summary": f"Print Sticker Status, {self.printer_status_data_label.cget('text')}"
            }
        )
        
    # def send_to_printer(self):
    #     print(f"send_to_printer")
    #     global qrCode_data
    #     global manualCode_data
    #     global break_printer

    #     if qrCode_data and manualCode_data:
    #         qrcode = qrCode_data
    #         manualcode = manualCode_data
    #     else:
    #         qrcode = ""
    #         manualcode =""

    #     if qrcode and manualcode:
    #         logger.info(f"Print Sticker, QR code payload = {qrcode}")
    #         print(f"Print Sticker, QR code payload = {qrcode}")
    #         logger.info(f"Print Sticker, Manual Code = {manualcode}")
    #         print(f"Print Sticker, Manual Code = {manualcode}")
    #         print_option_str = self.print_option_response.get()
    #         sendToPrinterFunc(qrcode, manualcode, print_option_str)
    #         logger.info(f"Print Sticker: Done")
    #         print(f"Print Sticker: Done")
    #         self.printer_status_data_label.config(text="Printed", fg="green", font=("Helvetica", 10, "bold"))
    #     else:
    #         logger.info(f"Print Sticker: Failed")
    #         print(f"Print Sticker: Failed")
    #         logger.error("Please select a Cert ID first before printing.")
    #         print("Please select a Cert ID first before printing.")
    #         self.printer_status_data_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

    #     break_printer = 1
    
    
    # Function: send_to_printer
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def send_to_printer(self):
        global qrCode_data
        global manualCode_data
        global break_printer

        # Validate required data
        if not qrCode_data:
            logger.error("QR Code data is empty.")
            self.datadog_logging(
                "error",
                {
                        "summary": "QR Code data is empty.",
                    }
            )
            print("QR Code data is empty.")
            self.printer_status_data_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
            final_status = "Failed"
            return

        if not manualCode_data:
            logger.error("Manual Code data is empty.")
            self.datadog_logging(
                "error",
                {
                        "summary": "Manual Code data is empty.",
                }
)
            print("Manual Code data is empty.")
            self.printer_status_data_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
            final_status = "Failed"
            return

        # Log the initial details
        qrcode = qrCode_data
        manualcode = manualCode_data
        print_option_str = self.print_option_response.get()
        include_sn_var = self.include_sn_var.get()

        logger.info(f"Print Sticker: QR code payload = {qrcode}, Manual code payload = {manualcode}, Print Option = {print_option_str}, Include SN = {include_sn_var}")
        self.datadog_logging(
            "info",
            {
                    "summary": "Printing Sticker"
            }
        )
        print(f"Print Sticker: Details\n  QR Code: {qrcode}\n  Manual Code: {manualcode}\n  Print Option: {print_option_str}, Include SN: {include_sn_var}")

        # Send data to the printer
        try:
            sendToPrinterFunc(qrcode, manualcode, print_option_str, include_sn_var)
            logger.info("Print Sticker: Success")
            self.datadog_logging(
                "info",
                {
                        "summary": "Print Sticker Success",
                }
            )
            print("Print Sticker: Success")
            self.printer_status_data_label.config(text="Printed", fg="green", font=("Helvetica", 10, "bold"))
            final_status = "Pass"

        except Exception as e:
            logger.error(f"Print Sticker: Failed. Error: {str(e)}")
            self.datadog_logging(
                "error",
                {
                        "summary": "Print Sticker Failed",
                }
            )
            print(f"Print Sticker: Failed. Error: {str(e)}")
            self.printer_status_data_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
            final_status = "Failed"
            return

        # Set break flag for printer interruption
        break_printer = 1

        # Log final status
        self.datadog_logging(
            "info" if final_status == "Pass" else "error",
            {
                    "summary": "Print Sticker Status",
                    "details": {
                        "Result": final_status
                    }
            }
        )


    def retrieve_device_data(self, database_file_path, order_number, mac_address):
        if not mac_address:
            logger.info("Device MAC address not available")
            print("retrieve_device_data: Device MAC address not available")
            return ""

        try:
            database_file = open (database_file_path, "r")
        except FileNotFoundError:
            pass
        else:
            for database in database_file:
                database_str = str(database.strip())
                # print(database_str)
                data_str = database_str.split(',')
                orderNum_data_str = str(data_str[0])
                macAddress_data_str = str(data_str[1])
                serialID_data_str = str(data_str[2])
                certID_data_str = str(data_str[3])
                secureCertPartition_data_str = str(data_str[4])
                commissionableDataPartition_data_str = str(data_str[5])
                qrCode_data_str = str(data_str[6])
                manualCode_data_str = str(data_str[7])
                discriminator_data_str = str(data_str[8])
                passcode_data_str = str(data_str[9])
                # print(orderNum_data_str)
                # print(macAddress_data_str)
                # print(serialID_data_str)
                # print(certID_data_str)
                # print(secureCertPartition_data_str)
                # print(commissionableDataPartition_data_str)
                # print(qrCode_data_str)
                # print(manualCode_data_str)
                # print(discriminator_data_str)
                # print(passcode_data_str)
                macAddress_data_array = macAddress_data_str.split(": ")
                # print(macAddress_data_array[0])
                # print(macAddress_data_array[1])
                if str(mac_address) == macAddress_data_array[1]:
                    orderNum_data_array = orderNum_data_str.split(": ")
                    if str(order_number) == orderNum_data_array[1]:
                        logger.info(str(mac_address) + " found in " + str(database_file_path))
                        logger.info("Data = " + str(database_str))
                        print(str(mac_address) + " found in " + str(database_file_path))
                        print("Data = " + str(database_str))
                        database_file.close()
                        return database_str
                    else:
                        pass
                else:
                    pass
            database_file.close()

        logger.info(str(mac_address) + " not found in " + str(database_file_path))
        print(str(mac_address) + " not found in " + str(database_file_path))
        try:
            database_file = open (database_file_path, "r")
        except FileNotFoundError:
            pass
        else:
            for database in database_file:
                database_str = str(database.strip())
                # print(database_str)
                data_str = database_str.split(',')
                orderNum_data_str = str(data_str[0])
                macAddress_data_str = str(data_str[1])
                serialID_data_str = str(data_str[2])
                certID_data_str = str(data_str[3])
                secureCertPartition_data_str = str(data_str[4])
                commissionableDataPartition_data_str = str(data_str[5])
                qrCode_data_str = str(data_str[6])
                manualCode_data_str = str(data_str[7])
                discriminator_data_str = str(data_str[8])
                passcode_data_str = str(data_str[9])
                # print(orderNum_data_str)
                # print(macAddress_data_str)
                # print(serialID_data_str)
                # print(certID_data_str)
                # print(secureCertPartition_data_str)
                # print(commissionableDataPartition_data_str)
                # print(qrCode_data_str)
                # print(manualCode_data_str)
                # print(discriminator_data_str)
                # print(passcode_data_str)
                macAddress_data_array = macAddress_data_str.split(": ")
                # print(macAddress_data_array[0])
                # print(macAddress_data_array[1])
                if not macAddress_data_array[1]:
                    orderNum_data_array = orderNum_data_str.split(": ")
                    if str(order_number) == orderNum_data_array[1]:
                        logger.info("Return available data slot")
                        logger.info(f"Data = {database_str}")
                        print("Return available data slot")
                        print(f"Data = {database_str}")
                        database_file.close()
                        return database_str
                    else:
                        pass
                else:
                    pass
            print("No available data slot")
            database_file.close()
            return ""

    def parse_device_data(self, database_data, mac_address):
        global device_data
        global orderNum_label
        global macAddress_label
        global serialID_label
        global certID_label
        global secureCertPartition_label
        global commissionableDataPartition_label
        global qrCode_label
        global manualCode_label
        global discriminator_label
        global passcode_label
        global orderNum_data
        global macAddress_esp32s3_data
        global serialID_data
        global certID_data
        global secureCertPartition_data
        global commissionableDataPartition_data
        global qrCode_data
        global manualCode_data
        global discriminator_data
        global passcode_data

        if not mac_address:
            logger.info("Device MAC address not available")
            print("parse_device_data: Device MAC address not available")
            return ""

        data_str = database_data.split(',')
        orderNum_data_str = str(data_str[0])
        macAddress_data_str = str(data_str[1])
        serialID_data_str = str(data_str[2])
        certID_data_str = str(data_str[3])
        secureCertPartition_data_str = str(data_str[4])
        commissionableDataPartition_data_str = str(data_str[5])
        qrCode_data_str = str(data_str[6])
        manualCode_data_str = str(data_str[7])
        discriminator_data_str = str(data_str[8])
        passcode_data_str = str(data_str[9])
        # print(orderNum_data_str)
        # print(macAddress_data_str)
        # print(serialID_data_str)
        # print(certID_data_str)
        # print(secureCertPartition_data_str)
        # print(commissionableDataPartition_data_str)
        # print(qrCode_data_str)
        # print(manualCode_data_str)
        # print(discriminator_data_str)
        # print(passcode_data_str)
        orderNum_data_array = orderNum_data_str.split(": ")
        orderNum_label = orderNum_data_array[0]
        orderNum_data = orderNum_data_array[1]
        # print(orderNum_label)
        # print(orderNum_data)
        macAddress_data_array = macAddress_data_str.split(": ")
        macAddress_label = macAddress_data_array[0]
        # macAddress_esp32s3_data = macAddress_data_array[1]
        macAddress_esp32s3_data = mac_address
        # print(macAddress_label)
        # print(macAddress_esp32s3_data)
        serialID_data_array = serialID_data_str.split(": ")
        serialID_label = serialID_data_array[0]
        serialID_data = serialID_data_array[1]
        # print(serialID_label)
        # print(serialID_data)
        certID_data_array = certID_data_str.split(": ")
        certID_label = certID_data_array[0]
        certID_data = certID_data_array[1]
        # print(certID_label)
        # print(certID_data)
        secureCertPartition_data_array = secureCertPartition_data_str.split(": ")
        secureCertPartition_label = secureCertPartition_data_array[0]
        secureCertPartition_data = secureCertPartition_data_array[1]
        # print(secureCertPartition_label)
        # print(secureCertPartition_data)
        commissionableDataPartition_data_array = commissionableDataPartition_data_str.split(": ")
        commissionableDataPartition_label = commissionableDataPartition_data_array[0]
        commissionableDataPartition_data = commissionableDataPartition_data_array[1]
        # print(commissionableDataPartition_label)
        # print(commissionableDataPartition_data)
        qrCode_data_array = qrCode_data_str.split(": ")
        qrCode_label = qrCode_data_array[0]
        qrCode_data = qrCode_data_array[1]
        # print(qrCode_label)
        # print(qrCode_data)
        manualCode_data_array = manualCode_data_str.split(": ")
        manualCode_label = manualCode_data_array[0]
        manualCode_data = manualCode_data_array[1]
        # print(manualCode_label)
        # print(manualCode_data)
        discriminator_data_array = discriminator_data_str.split(": ")
        discriminator_label = discriminator_data_array[0]
        discriminator_data = discriminator_data_array[1]
        # print(discriminator_label)
        # print(discriminator_data)
        passcode_data_array = passcode_data_str.split(": ")
        passcode_label = passcode_data_array[0]
        passcode_data = passcode_data_array[1]
        # print(passcode_label)
        # print(passcode_data)

    def get_driver_for_device(self, device_node):
        context = pyudev.Context()

        info = "error"

        # Iterate through all devices in the 'usb' subsystem
        for device in context.list_devices(subsystem='usb-serial'):
            str_device_node = str(device_node)
            if device.device_path.endswith(str_device_node.split("/dev/")[1].strip()):

            # # Check the kernel version of the device
            # device_kernel_version = device.get('KERNEL', str(device_node))
            
            # # print(device_kernel_version)

            # # If the kernel version matches the specified version, retrieve driver info
            # if device_kernel_version and device_kernel_version == str(device_node):

                devpath = device.device_path
                vendor = device.get('ID_VENDOR_ID', 'unknown')
                product = device.get('ID_MODEL_ID', 'unknown')
                serial = device.get('ID_SERIAL_SHORT', 'unknown')
                driver = device.get('DRIVER', 'No driver bound')

                # Print device information
                print(f"Device Path: {devpath}")
                print(f"  Vendor ID: {vendor}")
                print(f"  Product ID: {product}")
                print(f"  Serial: {serial}")
                print(f"  Driver: {driver}\n")

                info = str(driver)

        return info


    # Function: test_serialport2identify
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def test_serialport2identify(self, port, baudrate):
        
        try:
            # Open serial port
            ser = serial.Serial(port, baudrate, timeout=1)  # Update with the appropriate port
        except serial.SerialException as e:
            # Handle error
            logger.error(f"Error opening serial port: {e}")
            self.datadog_logging(
                "error",
                {
                        "summary": "Serial Port Error"
                }
            )
            print(f"Error opening serial port: {e}")
        else:
            # This block runs if no exception was raised
            ser.rts = False
            time.sleep(0.2)
            ser.rts = True
            time.sleep(0.2)
            ser.rts = False
            response = ser.readline()
            response_decoded = response.decode("utf-8", errors='replace').strip()
            # print(f"Response from device: {response.decode().strip()}")
            # Close the serial port
            ser.close()
        finally:
            # This block runs no matter what (even if there was an error)
            pass

        return response_decoded 

    def refresh_order_number_list(self):
        self.refresh_order_number_list_thread = Thread(target=self.refresh_order_number_list_thread_task)
        self.refresh_order_number_list_thread.start()

    def refresh_order_number_list_thread_task(self):
        global device_data_file_path

        self.refresh_order_number_button.config(state=tk.DISABLED)

        self.order_number_dropdown_list.set("")

        order_numbers = self.read_order_numbers(device_data_file_path)

        self.order_number_dropdown_list.config(values=order_numbers)
        self.order_number_dropdown_list.grid()

        # print("Refresh order number list completed")
        messagebox.showinfo("Info", "Refresh Completed")

        self.refresh_order_number_button.config(state=tk.NORMAL)

    def refresh_com_ports_list(self):
        self.refresh_com_ports_list_thread = Thread(target=self.refresh_com_ports_list_thread_task)
        self.refresh_com_ports_list_thread.start()

    def refresh_com_ports_list_thread_task(self):

        self.refresh_com_ports_button.config(state=tk.DISABLED)

        self.port_dropdown.set("")
        self.port_dropdown1.set("")
        self.port_dropdown2.set("")
        self.port_dropdown3.set("")

        for port in serial.tools.list_ports.comports():
            test_data = self.read_device_model(port.device, 115200)
            print(f"{port.device} = {test_data}")
            if f"{test_data}" == "ESP32-S3":
                # pass
                part = self.get_driver_for_device(port.device)
                print(f"{port.device} = {part}")
                if part == "cp210x":
                    print(f"Set {port.device} to ESP32S3 Module Port")
                    self.port_dropdown3.set(port.device)
                elif part == "ftdi_sio":
                    print(f"Set {port.device} to ESP32S3 Flash Port")
                    self.port_dropdown.set(port.device)
                else:
                    print("Auto detect port failed")
            elif f"{test_data}" == "ESP32-H2":
                print(f"Set {port.device} to ESP32H2 Flash Port")
                self.port_dropdown2.set(port.device)
            else:
                # pass
                part = self.get_driver_for_device(port.device)
                print(f"{port.device} = {part}")
                if part == "cp210x":
                    print(f"Set {port.device} to ESP32S3 Module Port")
                    self.port_dropdown3.set(port.device)
                elif part == "ch341-uart":
                    print(f"Set {port.device} to ESP32S3 Factory Port")
                    self.port_dropdown1.set(port.device)
                # elif part == "ftdi_sio":
                #     print(f"Set {port.device} to ESP32H2 Flash Port")
                #     self.port_dropdown2.set(port.device)
                else:
                    print("Auto detect port failed")

        if self.port_dropdown.get() == "" or self.port_dropdown.get() == None:
            print("Fail to detect ESP32S3 Flash Port")
            messagebox.showerror("Error", "Fail to detect ESP32S3 Flash Port")

        if self.port_dropdown1.get() == "" or self.port_dropdown1.get() == None:
            print("Fail to detect ESP32S3 Factory Port")
            messagebox.showerror("Error", "Fail to detect ESP32S3 Factory Port")

        if self.port_dropdown2.get() == "" or self.port_dropdown2.get() == None:
            print("Fail to detect ESP32H2 Flash Port")
            messagebox.showerror("Error", "Fail to detect ESP32H2 Flash Port")

        # if self.port_dropdown3.get() == "" or self.port_dropdown3.get() == None:
        #     print("Fail to detect ESP32S3 Module Port")
        #     messagebox.showerror("Error", "Fail to detect ESP32S3 Module Port")

        # print("Refresh com ports list completed")
        messagebox.showinfo("Info", "Refresh Completed")

        self.refresh_com_ports_button.config(state=tk.NORMAL)
            

    def create_widgets(self):
        global device_data_file_path
        
        order_numbers = self.read_order_numbers(device_data_file_path)

        # Create a frame for the canvas
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Create a canvas and add a scrollbar
        self.canvas = tk.Canvas(self.canvas_frame)

        # Vertical scrollbar
        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Horizontal scrollbar
        self.h_scrollbar = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set)

        # Pack the scrollbars
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Pack the canvas
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create another frame inside the canvas
        self.scrollable_frame = tk.Frame(self.canvas)

        # Bind the scrollable frame's Configure event to update the canvas scroll region
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Configure the weight for the scrollable_frame to expand
        self.scrollable_frame.grid_rowconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.serial_baud_frame = tk.Frame(self.scrollable_frame)
        self.serial_baud_frame.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)

        self.exit_button = ttk.Button(self.serial_baud_frame, text="Exit", command=self.root.quit)
        self.exit_button.grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)

        self.port_label = tk.Label(self.serial_baud_frame, text="ESP32S3 Flash Port/ESP32S3烧录端口:")
        self.port_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.port_var = tk.StringVar()
        self.port_dropdown = ttk.Combobox(self.serial_baud_frame, textvariable=self.port_var)
        self.port_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.port_dropdown['values'] = [port.device for port in serial.tools.list_ports.comports()]
        for port in serial.tools.list_ports.comports():
            # print(str(port.device))
            if str(port.device) == "/dev/ttyUSB0":
                self.port_dropdown.set(port.device)
            elif str(port.device) == "/dev/ttyACM0":
                self.port_dropdown.set(port.device)

        self.baud_label = tk.Label(self.serial_baud_frame, text="Baud Rate/波特率:")
        self.baud_label.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        # self.baud_label.grid_forget()

        self.baud_var = tk.StringVar()
        self.baud_dropdown = ttk.Combobox(self.serial_baud_frame, textvariable=self.baud_var)
        self.baud_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.baud_dropdown['values'] = ["9600", "115200", "460800", "921600", "1500000"]
        self.baud_dropdown.set("1500000")
        # self.baud_dropdown.set("460800")
        # self.baud_dropdown.grid_forget()

        self.flash_button = ttk.Button(self.serial_baud_frame, text="Flash FW", command=None)
        self.flash_button.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)

        self.cert_flash_button = ttk.Button(self.serial_baud_frame, text="Flash Cert", command=self.flash_cert)
        self.cert_flash_button.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)

        self.port_label1 = tk.Label(self.serial_baud_frame, text="ESP32S3 Factory Port/ESP32S3工厂模式端口:")
        self.port_label1.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.port_var1 = tk.StringVar()
        self.port_dropdown1 = ttk.Combobox(self.serial_baud_frame, textvariable=self.port_var1)
        self.port_dropdown1.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.port_dropdown1['values'] = [port.device for port in serial.tools.list_ports.comports()]
        for port in serial.tools.list_ports.comports():
            # print(str(port.device))
            if str(port.device) == "/dev/ttyUSB1":
                self.port_dropdown1.set(port.device)

        self.baud_label1 = tk.Label(self.serial_baud_frame, text="Baud Rate/波特率:")
        self.baud_label1.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        # self.baud_label1.grid_forget()

        self.baud_var1 = tk.StringVar()
        self.baud_dropdown1 = ttk.Combobox(self.serial_baud_frame, textvariable=self.baud_var1)
        self.baud_dropdown1.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        self.baud_dropdown1['values'] = ["9600", "115200", "460800", "921600", "1500000"]
        self.baud_dropdown1.set("115200")
        # self.baud_dropdown1.grid_forget()

        self.open_port_button = ttk.Button(self.serial_baud_frame, text="Open Port", command=self.open_serial_port)
        self.open_port_button.grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)

        self.close_port_button = ttk.Button(self.serial_baud_frame, text="Close Port", command=self.close_serial_port)
        self.close_port_button.grid(row=1, column=5, padx=5, pady=5, sticky=tk.W)

        self.read_device_mac_button = ttk.Button(self.serial_baud_frame, text="Read Device MAC", command=self.get_device_mac)
        self.read_device_mac_button.grid(row=1, column=6, padx=5, pady=5, sticky=tk.W)

        self.write_device_serialnumber_button = ttk.Button(self.serial_baud_frame, text="Write S/N", command=self.send_serial_number)
        self.write_device_serialnumber_button.grid(row=1, column=7, padx=5, pady=5, sticky=tk.W)

        self.write_device_mtqr_button = ttk.Button(self.serial_baud_frame, text="Write MTQR", command=self.send_mqtr)
        self.write_device_mtqr_button.grid(row=1, column=8, padx=5, pady=5, sticky=tk.W)

        self.read_atbeam_temp_button = ttk.Button(self.serial_baud_frame, text="Read ATBeam Temp", command=self.get_atbeam_temp)
        self.read_atbeam_temp_button.grid(row=1, column=9, padx=5, pady=5, sticky=tk.W)

        self.read_atbeam_humid_button = ttk.Button(self.serial_baud_frame, text="Read ATBeam Humid", command=self.get_atbeam_humid)
        self.read_atbeam_humid_button.grid(row=1, column=10, padx=5, pady=5, sticky=tk.W)

        self.port_label2 = tk.Label(self.serial_baud_frame, text="ESP32H2 Flash Port/ESP32H2烧录端口:")
        self.port_label2.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        self.refresh_com_ports_button = ttk.Button(self.serial_baud_frame, text="Refresh/刷新", command=self.refresh_com_ports_list)
        self.refresh_com_ports_button.grid(row=0, column=20, padx=5, pady=5, sticky=tk.W)

        self.port_var2 = tk.StringVar()
        self.port_dropdown2 = ttk.Combobox(self.serial_baud_frame, textvariable=self.port_var2)
        self.port_dropdown2.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.port_dropdown2['values'] = [port.device for port in serial.tools.list_ports.comports()]
        for port in serial.tools.list_ports.comports():
            # print(str(port.device))
            if str(port.device) == "/dev/ttyUSB2":
                self.port_dropdown2.set(port.device)

        self.baud_label2 = tk.Label(self.serial_baud_frame, text="Baud Rate/波特率:")
        self.baud_label2.grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)
        # self.baud_label2.grid_forget()

        self.baud_var2 = tk.StringVar()
        self.baud_dropdown2 = ttk.Combobox(self.serial_baud_frame, textvariable=self.baud_var2)
        self.baud_dropdown2.grid(row=2, column=3, padx=5, pady=5, sticky=tk.W)
        self.baud_dropdown2['values'] = ["9600", "115200", "460800", "921600", "1500000"]
        self.baud_dropdown2.set("1500000")
        # self.baud_dropdown2.set("460800")
        # self.baud_dropdown2.grid_forget()

        self.port_label3 = tk.Label(self.serial_baud_frame, text="ESP32S3 Module Port/ESP32S3模块端口:")
        self.port_label3.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)

        self.port_var3 = tk.StringVar()
        self.port_dropdown3 = ttk.Combobox(self.serial_baud_frame, textvariable=self.port_var3)
        self.port_dropdown3.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        self.port_dropdown3['values'] = [port.device for port in serial.tools.list_ports.comports()]
        for port in serial.tools.list_ports.comports():
            # print(str(port.device))
            if str(port.device) == "/dev/ttyUSB3":
                self.port_dropdown3.set(port.device)

        self.baud_label3 = tk.Label(self.serial_baud_frame, text="Baud Rate/波特率:")
        self.baud_label3.grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)
        # self.baud_label1.grid_forget()

        self.baud_var3 = tk.StringVar()
        self.baud_dropdown3 = ttk.Combobox(self.serial_baud_frame, textvariable=self.baud_var3)
        self.baud_dropdown3.grid(row=3, column=3, padx=5, pady=5, sticky=tk.W)
        self.baud_dropdown3['values'] = ["9600", "115200", "460800", "921600", "1500000"]
        self.baud_dropdown3.set("1500000")
        # self.baud_dropdown3.set("460800")
        # self.baud_dropdown1.grid_forget()

        self.check_module_button = ttk.Button(self.serial_baud_frame, text="Check Module/检查模块", command=self.start_check_module)
        self.check_module_button.grid(row=3, column=20, padx=5, pady=5, sticky=tk.W)

        #self.disable_frame(self.serial_baud_frame)
        #self.serial_baud_frame.grid_forget()
        self.flash_button.grid_forget()
        self.cert_flash_button.grid_forget()
        self.flash_button.grid_forget()
        self.open_port_button.grid_forget()
        self.close_port_button.grid_forget()
        self.read_device_mac_button.grid_forget()
        self.write_device_serialnumber_button.grid_forget()
        self.write_device_mtqr_button.grid_forget()
        self.read_atbeam_temp_button.grid_forget()
        self.read_atbeam_humid_button.grid_forget()
        self.exit_button.grid_forget()

        self.text_frame = tk.Frame(self.scrollable_frame)
        self.text_frame.grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)

        self.send_entry_frame = ttk.Entry(self.text_frame, width=50)
        self.send_entry_frame.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        self.send_button = ttk.Button(self.text_frame, text="Send", command=lambda: self.sendEntry.send_entry_command(self.send_entry_frame))
        self.send_button.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        self.disable_frame(self.text_frame)
        self.text_frame.grid_forget()

        self.servo_frame = tk.Frame(self.scrollable_frame)
        self.servo_frame.grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)

        self.angle_label = tk.Label(self.servo_frame, text="Enter servo angle:")
        self.angle_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.angle_entry = tk.Entry(self.servo_frame)
        self.angle_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        self.duration_label = tk.Label(self.servo_frame, text="Enter pressing duration:")
        self.duration_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.duration_entry = tk.Entry(self.servo_frame)
        self.duration_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.pressing_time_label = tk.Label(self.servo_frame, text="Enter pressing time:")
        self.pressing_time_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        self.pressing_time_entry = tk.Entry(self.servo_frame)
        self.pressing_time_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        self.disable_frame(self.servo_frame)
        self.servo_frame.grid_forget()

        self.dmm_frame = tk.Frame(self.scrollable_frame)
        self.dmm_frame.grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)

        self.read_temp_aht20_button = ttk.Button(self.dmm_frame, text="Read Temperature Sensor", command=self.read_temp_aht20)
        self.read_temp_aht20_button.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.read_temp_aht20_button.grid_forget()

        self.read_humid_aht20_button = ttk.Button(self.dmm_frame, text="Read Humidity Sensor", command=self.read_humid_aht20)
        self.read_humid_aht20_button.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
        self.read_humid_aht20_button.grid_forget()

        # Order Number
        self.order_number_frame = tk.Frame(self.scrollable_frame)
        self.order_number_frame.grid(row=5, column=0, padx=10, pady=10, sticky=tk.W)

        self.order_number_label = tk.Label(self.order_number_frame, text="Order Number/订单号:")
        self.order_number_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.order_number_dropdown = tk.StringVar()
        self.order_number_dropdown_list = ttk.Combobox(self.order_number_frame, textvariable=self.order_number_dropdown, values=order_numbers)
        # self.order_number_dropdown_list.bind("<<ComboboxSelected>>", self.on_order_selected)
        self.order_number_dropdown_list.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        self.selected_order_no_label = tk.Label(self.order_number_frame, text="")
        self.selected_order_no_label.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        self.cert_id_label = tk.Label(self.order_number_frame, text="Select Cert ID:")
        self.cert_id_label.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.cert_id_label.grid_forget()

        self.refresh_order_number_button = ttk.Button(self.order_number_frame, text="Refresh/刷新", command=self.refresh_order_number_list)
        self.refresh_order_number_button.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)

        cert_id_var = tk.StringVar()
        self.cert_id_dropdown = ttk.Combobox(self.order_number_frame, textvariable=cert_id_var)
        self.cert_id_dropdown.bind("<<ComboboxSelected>>", self.on_select_cert_id)
        self.cert_id_dropdown.grid_forget()

        self.cert_status_label = tk.Label(self.order_number_frame, text="")
        self.cert_status_label.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)

        # Start and Stop buttons
        self.control_frame = tk.Frame(self.scrollable_frame)
        self.control_frame.grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)

        self.start_button = ttk.Button(self.control_frame, text="Start/开始", command=self.start_process)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.flash_button = ttk.Button(self.control_frame, text="flash/仅写入固件", command=self.flash_process)
        self.flash_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        self.retest_button = ttk.Button(self.control_frame, text="Retest/仅测试", command=self.retest_process)
        self.retest_button.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        self.reload_ir_button = ttk.Button(self.control_frame, text="Reload IR/重装红外", command=self.reload_ir_thread_task)
        self.reload_ir_button.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        self.stop_button = ttk.Button(self.control_frame, text="Stop", command=None)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.stop_button.grid_forget()

        self.reset_button = ttk.Button(self.control_frame, text="Reset", command=self.reset_tasks)
        self.reset_button.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.reset_button.grid_forget()

        self.retest_label = tk.Label(self.control_frame, text="Retest MAC:")
        self.retest_label.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.retest_label.grid_forget()

        self.retest_mac_input = tk.Entry(self.control_frame)
        self.retest_mac_input.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.retest_mac_input.grid_forget()

        # self.retest_button = ttk.Button(self.control_frame, text="Retest", command=None)
        # self.retest_button.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        # self.retest_button.grid_forget()

        self.notes_label = tk.Label(self.control_frame, text="<<- Select order number to start/首先选择订单号", font=("Helvetica", 10, "bold"))
        self.notes_label.grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)

        # Group 1
        # Flash FW, Flash Cert, Factory Mode, Read Device MAC, Read Product Name, Write Device S/N, Write Device MTQR, 3.3V, 5V, Button Pressed, Sensor Temperature, Sensor Humidity
        self.group1_frame = tk.Frame(self.scrollable_frame, highlightbackground="black", highlightcolor="black", highlightthickness=2, bd=2)
        self.group1_frame.grid(row=7, column=0, padx=10, pady=10, sticky=tk.W)

        self.auto_frame_label = tk.Label(self.group1_frame, text="Semi Auto Test/半自动测试", font=("Helvetica", 10, "bold"))
        self.auto_frame_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.status_fw_availability_label = tk.Label(self.group1_frame, text="Firmware Check: ")
        self.status_fw_availability_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        # self.status_fw_availability_label.grid_forget()
        
        self.result_fw_availability_index = tk.Label(self.group1_frame, text="ESP32S3: ")
        self.result_fw_availability_index.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        # self.result_fw_availability_index.grid_forget()
        
        self.fw_availability_label = tk.Label(self.group1_frame, text="Not Yet")
        self.fw_availability_label.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        # self.fw_availability_label.grid_forget()
        
        self.status_espfuse_s3 = tk.Label(self.group1_frame, text="eFuse Check: ")
        self.status_espfuse_s3.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.result_espfuse_s3_index = tk.Label(self.group1_frame, text="ESP32S3: ")
        self.result_espfuse_s3_index.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.result_espfuse_s3 = tk.Label(self.group1_frame, text="Not Yet")
        self.result_espfuse_s3.grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)

        self.read_mac_address_label = tk.Label(self.group1_frame, text="MAC Address/MAC地址: ")
        self.read_mac_address_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_mac_address_s3_index = tk.Label(self.group1_frame, text="ESP32S3: ")
        self.result_mac_address_s3_index.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        self.result_mac_address_s3_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_mac_address_s3_label.grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)

        self.result_mac_address_h2_index = tk.Label(self.group1_frame, text="ESP32H2: ")
        self.result_mac_address_h2_index.grid(row=3, column=3, padx=5, pady=5, sticky=tk.W)

        self.result_mac_address_h2_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_mac_address_h2_label.grid(row=3, column=4, padx=5, pady=5, sticky=tk.W)

        self.status_flashing_fw = tk.Label(self.group1_frame, text="Flashing Firmware/写入固件: ")
        self.status_flashing_fw.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_flashing_fw_s3_index = tk.Label(self.group1_frame, text="ESP32S3: ")
        self.result_flashing_fw_s3_index.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)

        self.result_flashing_fw_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_flashing_fw_label.grid(row=4, column=2, padx=5, pady=5, sticky=tk.W)

        self.result_flashing_fw_h2_index = tk.Label(self.group1_frame, text="ESP32H2: ")
        self.result_flashing_fw_h2_index.grid(row=4, column=3, padx=5, pady=5, sticky=tk.W)

        self.result_flashing_fw_h2_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_flashing_fw_h2_label.grid(row=4, column=4, padx=5, pady=5, sticky=tk.W)

        self.status_flashing_cert = tk.Label(self.group1_frame, text="Flashing DAC/写入DAC: ")
        self.status_flashing_cert.grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_flashing_cert_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_flashing_cert_label.grid(row=5, column=1, padx=5, pady=5, sticky=tk.W)

        self.status_factory_mode = tk.Label(self.group1_frame, text="Factory Mode/工厂模式: ")
        self.status_factory_mode.grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_factory_mode_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_factory_mode_label.grid(row=6, column=1, padx=5, pady=5, sticky=tk.W)

        self.status_read_device_mac = tk.Label(self.group1_frame, text="Read Device MAC/读MAC地址: ")
        self.status_read_device_mac.grid(row=7, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_read_device_mac = tk.Label(self.group1_frame, text="Not Yet")
        self.result_read_device_mac.grid(row=7, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_mac = tk.Label(self.group1_frame, text="-")
        self.read_device_mac.grid(row=7, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_read_device_firmware_version = tk.Label(self.group1_frame, text="Read Device Firmware/读固件版本: ")
        self.status_read_device_firmware_version.grid(row=8, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_read_device_firmware_version = tk.Label(self.group1_frame, text="Not Yet")
        self.result_read_device_firmware_version.grid(row=8, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_firmware_version = tk.Label(self.group1_frame, text="-")
        self.read_device_firmware_version.grid(row=8, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_read_prod_name = tk.Label(self.group1_frame, text="Product Name/产品名称: ")
        self.status_read_prod_name.grid(row=9, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_read_prod_name = tk.Label(self.group1_frame, text="Not Yet")
        self.result_read_prod_name.grid(row=9, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_prod_name = tk.Label(self.group1_frame, text="-")
        self.read_prod_name.grid(row=9, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_write_device_sn = tk.Label(self.group1_frame, text="Write Device S/N/写入S/N号: ")
        self.status_write_device_sn.grid(row=10, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_write_serialnumber = tk.Label(self.group1_frame,text="Not Yet")
        self.result_write_serialnumber.grid(row=10, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_sn = tk.Label(self.group1_frame, text="-")
        self.read_device_sn.grid(row=10, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_read_device_matter_dac_vid = tk.Label(self.group1_frame, text="Read Device Matter DAC VID/读Matter DAC VID: ")
        self.status_read_device_matter_dac_vid.grid(row=11, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_read_device_matter_dac_vid = tk.Label(self.group1_frame, text="Not Yet")
        self.result_read_device_matter_dac_vid.grid(row=11, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_matter_dac_vid = tk.Label(self.group1_frame, text="-")
        self.read_device_matter_dac_vid.grid(row=11, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_read_device_matter_dac_pid = tk.Label(self.group1_frame, text="Read Device Matter DAC PID/读Matter DAC PID: ")
        self.status_read_device_matter_dac_pid.grid(row=12, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_read_device_matter_dac_pid = tk.Label(self.group1_frame, text="Not Yet")
        self.result_read_device_matter_dac_pid.grid(row=12, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_matter_dac_pid = tk.Label(self.group1_frame, text="-")
        self.read_device_matter_dac_pid.grid(row=12, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_read_device_matter_vid = tk.Label(self.group1_frame, text="Read Device Matter VID/读Matter VID: ")
        self.status_read_device_matter_vid.grid(row=13, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_read_device_matter_vid = tk.Label(self.group1_frame, text="Not Yet")
        self.result_read_device_matter_vid.grid(row=13, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_matter_vid = tk.Label(self.group1_frame, text="-")
        self.read_device_matter_vid.grid(row=13, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_read_device_matter_pid = tk.Label(self.group1_frame, text="Read Device Matter PID/读Matter PID: ")
        self.status_read_device_matter_pid.grid(row=14, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_read_device_matter_pid = tk.Label(self.group1_frame, text="Not Yet")
        self.result_read_device_matter_pid.grid(row=14, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_matter_pid = tk.Label(self.group1_frame, text="-")
        self.read_device_matter_pid.grid(row=14, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_read_device_matter_discriminator = tk.Label(self.group1_frame, text="Read Device Matter Discriminator/读Matter Discriminator: ")
        self.status_read_device_matter_discriminator.grid(row=15, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_read_device_matter_discriminator = tk.Label(self.group1_frame, text="Not Yet")
        self.result_read_device_matter_discriminator.grid(row=15, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_matter_discriminator = tk.Label(self.group1_frame, text="-")
        self.read_device_matter_discriminator.grid(row=15, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_write_device_mtqr = tk.Label(self.group1_frame, text="Write Device Matter QR/写入Matter二维码: ")
        self.status_write_device_mtqr.grid(row=16, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_write_mtqr = tk.Label(self.group1_frame, text="Not Yet")
        self.result_write_mtqr.grid(row=16, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_device_mtqr = tk.Label(self.group1_frame, text="-")
        self.read_device_mtqr.grid(row=16, column=2, padx=5, pady=5, sticky=tk.W)

        self.result_ir_def = tk.Label(self.group1_frame, text="Write IR Definition/写入红外线代码: ")
        self.result_ir_def.grid(row=17, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_ir_def_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_ir_def_label.grid(row=17, column=1, padx=5, pady=5, sticky=tk.W)

        self.status_save_device_data_label = tk.Label(self.group1_frame, text="Save Device Data/保存产品数据: ")
        self.status_save_device_data_label.grid(row=18, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_save_device_data_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_save_device_data_label.grid(row=18, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_save_device_data_label = tk.Label(self.group1_frame, text="-")
        self.read_save_device_data_label.grid(row=18, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_save_application_data_label = tk.Label(self.group1_frame, text="Save Application Data/保存应用程序数据: ")
        self.status_save_application_data_label.grid(row=19, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_save_application_data_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_save_application_data_label.grid(row=19, column=1, padx=5, pady=5, sticky=tk.W)

        self.read_save_application_data_label = tk.Label(self.group1_frame, text="-")
        self.read_save_application_data_label.grid(row=19, column=2, padx=5, pady=5, sticky=tk.W)

        self.status_5v_test = tk.Label(self.group1_frame, text="5V Test/5伏测试: ")
        self.status_5v_test.grid(row=20, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_5v_test = tk.Label(self.group1_frame, text="Not Yet")
        self.result_5v_test.grid(row=20, column=1, padx=5, pady=5, sticky=tk.W)

        self.dmm_5V_reader = tk.Label(self.group1_frame, text="-")
        self.dmm_5V_reader.grid(row=20, column=2, padx=5, pady=5, sticky=tk.W)

        self.input_5V_dmm = tk.Entry(self.group1_frame)
        self.input_5V_dmm.grid(row=20, column=3, padx=5, pady=5, sticky=tk.W)
        # self.input_5V_dmm.config(state=tk.DISABLED)

        self.submit_5V_dmm = ttk.Button(self.group1_frame, text="Submit/输入", command=lambda: self.dmm_reader_5V_value_manual(self.input_5V_dmm))
        self.submit_5V_dmm.grid(row=20, column=4, padx=5, pady=5, sticky=tk.W)
        self.submit_5V_dmm.config(state=tk.DISABLED)

        self.range_index_5V_dmm = tk.Label(self.group1_frame, text="Range/测试范围(±): ")
        self.range_index_5V_dmm.grid(row=20, column=5, padx=5, pady=5, sticky=tk.W)

        self.range_value_5V_dmm = tk.Label(self.group1_frame, text="-")
        self.range_value_5V_dmm.grid(row=20, column=6, padx=5, pady=5, sticky=tk.W)

        self.status_3_3v_test = tk.Label(self.group1_frame, text="3.3V Test/3.3伏测试: ")
        self.status_3_3v_test.grid(row=21, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_3_3v_test = tk.Label(self.group1_frame, text="Not Yet")
        self.result_3_3v_test.grid(row=21, column=1, padx=5, pady=5, sticky=tk.W)

        self.dmm_3_3V_reader = tk.Label(self.group1_frame, text="-")
        self.dmm_3_3V_reader.grid(row=21, column=2, padx=5, pady=5, sticky=tk.W)

        self.input_3_3V_dmm = tk.Entry(self.group1_frame)
        self.input_3_3V_dmm.grid(row=21, column=3, padx=5, pady=5, sticky=tk.W)
        # self.input_3_3V_dmm.config(state=tk.DISABLED)

        self.submit_3_3V_dmm = ttk.Button(self.group1_frame, text="Submit/输入", command=lambda: self.dmm_reader_3_3V_value_manual(self.input_3_3V_dmm))
        self.submit_3_3V_dmm.grid(row=21, column=4, padx=5, pady=5, sticky=tk.W)
        self.submit_3_3V_dmm.config(state=tk.DISABLED)

        self.range_index_3_3V_dmm = tk.Label(self.group1_frame, text="Range/测试范围(±): ")
        self.range_index_3_3V_dmm.grid(row=21, column=5, padx=5, pady=5, sticky=tk.W)

        self.range_value_3_3V_dmm = tk.Label(self.group1_frame, text="-")
        self.range_value_3_3V_dmm.grid(row=21, column=6, padx=5, pady=5, sticky=tk.W)

        self.status_atbeam_temp = tk.Label(self.group1_frame, text="Temperature Test/温度测试: ")
        self.status_atbeam_temp.grid(row=22, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_temp_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_temp_label.grid(row=22, column=1, padx=5, pady=5, sticky=tk.W)

        self.atbeam_temp_index = tk.Label(self.group1_frame, text="Device/产品传感器: ")
        self.atbeam_temp_index.grid(row=22, column=2, padx=5, pady=5, sticky=tk.W)

        self.atbeam_temp_value = tk.Label(self.group1_frame, text="AT °C")
        self.atbeam_temp_value.grid(row=22, column=3, padx=5, pady=5, sticky=tk.W)

        self.ext_temp_index = tk.Label(self.group1_frame, text="External/外部传感器: ")
        self.ext_temp_index.grid(row=22, column=4, padx=5, pady=5, sticky=tk.W)

        self.ext_temp_value = tk.Label(self.group1_frame, text="Ext °C")
        self.ext_temp_value.grid(row=22, column=5, padx=5, pady=5, sticky=tk.W)

        self.ext_raw_temp_value = tk.Label(self.group1_frame, text="Ext Raw °C")
        self.ext_raw_temp_value.grid(row=22, column=6, padx=5, pady=5, sticky=tk.W)

        self.range_temp_index = tk.Label(self.group1_frame, text="Range/测试范围(±): ")
        self.range_temp_index.grid(row=22, column=7, padx=5, pady=5, sticky=tk.W)

        self.range_temp_value = tk.Label(self.group1_frame, text="-")
        self.range_temp_value.grid(row=22, column=8, padx=5, pady=5, sticky=tk.W)

        self.status_atbeam_humidity = tk.Label(self.group1_frame, text="Humidity Test/湿度测试: ")
        self.status_atbeam_humidity.grid(row=23, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_humid_label = tk.Label(self.group1_frame, text="Not Yet")
        self.result_humid_label.grid(row=23, column=1, padx=5, pady=5, sticky=tk.W)

        self.atbeam_humid_index = tk.Label(self.group1_frame, text="Device/产品传感器: ")
        self.atbeam_humid_index.grid(row=23, column=2, padx=5, pady=5, sticky=tk.W)

        self.atbeam_humid_value = tk.Label(self.group1_frame, text="AT %")
        self.atbeam_humid_value.grid(row=23, column=3, padx=5, pady=5, sticky=tk.W)

        self.ext_humid_index = tk.Label(self.group1_frame, text="External/外部传感器: ")
        self.ext_humid_index.grid(row=23, column=4, padx=5, pady=5, sticky=tk.W)

        self.ext_humid_value = tk.Label(self.group1_frame, text="Ext %")
        self.ext_humid_value.grid(row=23, column=5, padx=5, pady=5, sticky=tk.W)

        self.ext_raw_humid_value = tk.Label(self.group1_frame, text="Ext Raw %")
        self.ext_raw_humid_value.grid(row=23, column=6, padx=5, pady=5, sticky=tk.W)

        self.range_humid_index = tk.Label(self.group1_frame, text="Range/测试范围(±): ")
        self.range_humid_index.grid(row=23, column=7, padx=5, pady=5, sticky=tk.W)

        self.range_humid_value = tk.Label(self.group1_frame, text="-")
        self.range_humid_value.grid(row=23, column=8, padx=5, pady=5, sticky=tk.W)

        self.status_test_irrx = tk.Label(self.group1_frame, text="IR Receiver Test/红外线接收器测试: ")
        self.status_test_irrx.grid(row=24, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_test_irrx= tk.Label(self.group1_frame, text="Not Yet")
        self.result_test_irrx.grid(row=24, column=1, padx=5, pady=5, sticky=tk.W)

        self.test_irrx= tk.Label(self.group1_frame, text="-")
        self.test_irrx.grid(row=24, column=2, padx=5, pady=5, sticky=tk.W)

        # Group 2

        self.group2_frame = tk.Frame(self.scrollable_frame, highlightbackground="black", highlightcolor="black", highlightthickness=2, bd=2)
        self.group2_frame.grid(row=9, column=0, padx=10, pady=10, sticky=tk.W)

        self.group2_label = tk.Label(self.group2_frame, text="ESP32S3 Wi-Fi Test/ESP32S3 Wi-Fi测试", font=("Helvetica", 10, "bold"))
        self.group2_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.status_group2_factory_mode = tk.Label(self.group2_frame, text="Factory Mode/工厂模式: ")
        self.status_group2_factory_mode.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_group2_factory_mode = tk.Label(self.group2_frame, text="Not Yet")
        self.result_group2_factory_mode.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.status_group2_wifi_softap_label = tk.Label(self.group2_frame, text="Wi-Fi Soft AP: ")
        self.status_group2_wifi_softap_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_group2_wifi_softap = tk.Label(self.group2_frame, text="Not Yet")
        self.result_group2_wifi_softap.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        self.result_group2_wifi_softap_rssi = tk.Label(self.group2_frame, text="-")
        self.result_group2_wifi_softap_rssi.grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)

        self.range_group2_wifi_softap_rssi_index = tk.Label(self.group2_frame, text="Range/测试范围(>): ")
        self.range_group2_wifi_softap_rssi_index.grid(row=2, column=3, padx=5, pady=5, sticky=tk.W)

        self.range_group2_wifi_softap_rssi = tk.Label(self.group2_frame, text="-")
        self.range_group2_wifi_softap_rssi.grid(row=2, column=4, padx=5, pady=5, sticky=tk.W)

        self.result_group2_wifi_softap_ssid_index = tk.Label(self.group2_frame, text="SSID: ")
        self.result_group2_wifi_softap_ssid_index.grid(row=2, column=5, padx=5, pady=5, sticky=tk.W)

        self.result_group2_wifi_softap_ssid = tk.Label(self.group2_frame, text="-")
        self.result_group2_wifi_softap_ssid.grid(row=2, column=6, padx=5, pady=5, sticky=tk.W)

        self.status_group2_wifi_station = tk.Label(self.group2_frame, text="Wi-Fi Station: ")
        self.status_group2_wifi_station.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_group2_wifi_station = tk.Label(self.group2_frame, text="Not Yet")
        self.result_group2_wifi_station.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        self.result_group2_wifi_station_rssi = tk.Label(self.group2_frame, text="-")
        self.result_group2_wifi_station_rssi.grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)

        self.range_group2_wifi_station_rssi_index = tk.Label(self.group2_frame, text="Range/测试范围(>): ")
        self.range_group2_wifi_station_rssi_index.grid(row=3, column=3, padx=5, pady=5, sticky=tk.W)

        self.range_group2_wifi_station_rssi = tk.Label(self.group2_frame, text="-")
        self.range_group2_wifi_station_rssi.grid(row=3, column=4, padx=5, pady=5, sticky=tk.W)

        self.status_http_device_matter_discriminator = tk.Label(self.group2_frame, text="HTTP Device Matter Discriminator: ")
        self.status_http_device_matter_discriminator.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_http_device_matter_discriminator = tk.Label(self.group2_frame, text="Not Yet")
        self.result_http_device_matter_discriminator.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)

        self.http_device_matter_discriminator = tk.Label(self.group2_frame, text="-")
        self.http_device_matter_discriminator.grid(row=4, column=2, padx=5, pady=5, sticky=tk.W)

        # Group 3
        self.group3_frame = tk.Frame(self.scrollable_frame, highlightbackground="black", highlightcolor="black", highlightthickness=2, bd=2)
        self.group3_frame.grid(row=11, column=0, padx=10, pady=10, sticky=tk.W)

        self.group3_label = tk.Label(self.group3_frame, text="Manual Test/手动测试", font=("Helvetica", 10, "bold"))
        self.group3_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.status_button_label = tk.Label(self.group3_frame, text="Button Test/按钮测试: ")
        self.status_button_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_button_label = tk.Label(self.group3_frame, text="Not Yet")
        self.result_button_label.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.button_fail_button = ttk.Button(self.group3_frame, text="No/没有", command=self.button_fail)
        self.button_fail_button.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        self.button_fail_button.config(state=tk.DISABLED)

        # self.result_ir_def = tk.Label(self.group3_frame, text="IR Definition/红外线代码: ")
        # self.result_ir_def.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        # self.result_ir_def_label = tk.Label(self.group3_frame, text="Not Yet")
        # self.result_ir_def_label.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.status_rgb_red_label = tk.Label(self.group3_frame, text="Red LED/红灯: ")
        self.status_rgb_red_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_rgb_red_label = tk.Label(self.group3_frame, text="Not Yet")
        self.result_rgb_red_label.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_red = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_red_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_red.grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_red.config(state=tk.DISABLED)

        self.no_button_red = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_red_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_red.grid(row=2, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_red.config(state=tk.DISABLED)

        self.status_rgb_green_label = tk.Label(self.group3_frame, text="Green LED/绿灯: ")
        self.status_rgb_green_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_rgb_green_label = tk.Label(self.group3_frame, text="Not Yet")
        self.result_rgb_green_label.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_green = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_green_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_green.grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_green.config(state=tk.DISABLED)

        self.no_button_green = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_green_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_green.grid(row=3, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_green.config(state=tk.DISABLED)

        self.status_rgb_blue_label = tk.Label(self.group3_frame, text="Blue LED/蓝灯: ")
        self.status_rgb_blue_label.grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_rgb_blue_label = tk.Label(self.group3_frame, text="Not Yet")
        self.result_rgb_blue_label.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_blue = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_blue_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_blue.grid(row=4, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_blue.config(state=tk.DISABLED)

        self.no_button_blue = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_blue_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_blue.grid(row=4, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_blue.config(state=tk.DISABLED)

        self.status_rgb_off_label = tk.Label(self.group3_frame, text="Off LED/关灯: ")
        self.status_rgb_off_label.grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_rgb_off_label = tk.Label(self.group3_frame, text="Not Yet")
        self.result_rgb_off_label.grid(row=5, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_rgb_off = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_ir_rx_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_rgb_off.grid(row=5, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_rgb_off.config(state=tk.DISABLED)

        self.no_button_rgb_off = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_ir_rx_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_rgb_off.grid(row=5, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_rgb_off.config(state=tk.DISABLED)

        self.ir_led1_label = tk.Label(self.group3_frame, text="IR LED 1/红外线1: ")
        self.ir_led1_label.grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_ir_led1 = tk.Label(self.group3_frame, text="Not Yet")
        self.result_ir_led1.grid(row=6, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_ir_led1 = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_ir_led1_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_ir_led1.grid(row=6, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_ir_led1.config(state=tk.DISABLED)

        self.no_button_ir_led1 = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_ir_led1_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_ir_led1.grid(row=6, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_ir_led1.config(state=tk.DISABLED)

        self.ir_led2_label = tk.Label(self.group3_frame, text="IR LED 2/红外线2: ")
        self.ir_led2_label.grid(row=7, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_ir_led2 = tk.Label(self.group3_frame, text="Not Yet")
        self.result_ir_led2.grid(row=7, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_ir_led2 = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_ir_led2_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_ir_led2.grid(row=7, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_ir_led2.config(state=tk.DISABLED)

        self.no_button_ir_led2 = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_ir_led2_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_ir_led2.grid(row=7, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_ir_led2.config(state=tk.DISABLED)

        self.ir_led3_label = tk.Label(self.group3_frame, text="IR LED 3/红外线3: ")
        self.ir_led3_label.grid(row=8, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_ir_led3 = tk.Label(self.group3_frame, text="Not Yet")
        self.result_ir_led3.grid(row=8, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_ir_led3 = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_ir_led3_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_ir_led3.grid(row=8, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_ir_led3.config(state=tk.DISABLED)

        self.no_button_ir_led3 = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_ir_led3_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_ir_led3.grid(row=8, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_ir_led3.config(state=tk.DISABLED)

        self.ir_led4_label = tk.Label(self.group3_frame, text="IR LED 4/红外线4: ")
        self.ir_led4_label.grid(row=9, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_ir_led4 = tk.Label(self.group3_frame, text="Not Yet")
        self.result_ir_led4.grid(row=9, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_ir_led4 = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_ir_led4_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_ir_led4.grid(row=9, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_ir_led4.config(state=tk.DISABLED)

        self.no_button_ir_led4 = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_ir_led4_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_ir_led4.grid(row=9, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_ir_led4.config(state=tk.DISABLED)

        self.ir_led5_label = tk.Label(self.group3_frame, text="IR LED 5/红外线5: ")
        self.ir_led5_label.grid(row=10, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_ir_led5 = tk.Label(self.group3_frame, text="Not Yet")
        self.result_ir_led5.grid(row=10, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_button_ir_led5 = ttk.Button(self.group3_frame, text="Yes/有", command=lambda: self.update_ir_led5_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_button_ir_led5.grid(row=10, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_button_ir_led5.config(state=tk.DISABLED)

        self.no_button_ir_led5 = ttk.Button(self.group3_frame, text="No/没有", command=lambda: self.update_ir_led5_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_button_ir_led5.grid(row=10, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_button_ir_led5.config(state=tk.DISABLED)
        
        self.group3_frame.grid(row=11, column=0, padx=10, pady=10, sticky=tk.W)
        # self.add_image_next_to_frame()
        
        


        # Group 4
        self.group4_frame = tk.Frame(self.scrollable_frame, highlightbackground="black", highlightcolor="black", highlightthickness=2, bd=2)
        self.group4_frame.grid(row=12, column=0, padx=10, pady=10, sticky=tk.W)

        self.group4_label = tk.Label(self.group4_frame, text="ESP32H2 Test/ESP32H2测试", font=("Helvetica", 10, "bold"))
        self.group4_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.status_short_header = tk.Label(self.group4_frame, text="Short Header/排针短路: ")
        self.status_short_header.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_short_header = tk.Label(self.group4_frame, text="Not Yet")
        self.result_short_header.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_short_header = ttk.Button(self.group4_frame, text="Yes/有", command=lambda: self.update_status_short_header_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_short_header.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_short_header.config(state=tk.DISABLED)

        self.no_short_header = ttk.Button(self.group4_frame, text="No/没有", command=lambda: self.update_status_short_header_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_short_header.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_short_header.config(state=tk.DISABLED)

        self.status_factory_reset = tk.Label(self.group4_frame, text="Factory Reset/恢复出厂设置: ")
        self.status_factory_reset.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.status_factory_reset.grid_forget()

        self.result_factory_reset = tk.Label(self.group4_frame, text="Not Yet")
        self.result_factory_reset.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.result_factory_reset.grid_forget()

        self.status_h2_led_check = tk.Label(self.group4_frame, text="ESP32H2 Small LED Test/ESP32H2小红灯测试: ")
        self.status_h2_led_check.grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)

        self.result_h2_led_check = tk.Label(self.group4_frame, text="Not Yet")
        self.result_h2_led_check.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        self.yes_h2_led_check = ttk.Button(self.group4_frame, text="Yes/有", command=lambda: self.update_status_h2_led_label("Pass", fg="green", font=("Helvetica", 10, "bold")))
        self.yes_h2_led_check.grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)
        self.yes_h2_led_check.config(state=tk.DISABLED)

        self.no_h2_led_check = ttk.Button(self.group4_frame, text="No/没有", command=lambda: self.update_status_h2_led_label("Failed", fg="red", font=("Helvetica", 10, "bold")))
        self.no_h2_led_check.grid(row=3, column=3, padx=5, pady=5, sticky=tk.W)
        self.no_h2_led_check.config(state=tk.DISABLED)

        # Print
        self.printer_frame = tk.Frame(self.scrollable_frame, highlightbackground="black", highlightcolor="black", highlightthickness=2, bd=2)
        self.printer_frame.grid(row=13, column=0, padx=10, pady=10, sticky=tk.W)

        self.printer_label = tk.Label(self.printer_frame, text="Sticker Printing/打印贴纸", font=("Helvetica", 10, "bold"))
        self.printer_label.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        self.printer_ip_label = tk.Label(self.printer_frame, text="Printer Network IP/打印机网络IP地址:")
        self.printer_ip_label.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        self.printer_ip_label.grid_forget()

        self.printer_ip_var = tk.StringVar(value="10.10.23.220")
        self.printer_ip_entry = tk.Entry(self.printer_frame, textvariable=self.printer_ip_var)
        self.printer_ip_entry.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.printer_ip_entry.grid_forget()

        self.printer_port_label = tk.Label(self.printer_frame, text="Printer Network Port/打印机网络端口:")
        self.printer_port_label.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.printer_port_label.grid_forget()

        self.printer_port_var = tk.StringVar(value="9100")
        self.printer_port_entry = tk.Entry(self.printer_frame, textvariable=self.printer_port_var)
        self.printer_port_entry.grid(row=2, column=2, padx=5, pady=5, sticky=tk.W)
        self.printer_port_entry.grid_forget()

        self.printer_qrpayload_label = tk.Label(self.printer_frame, text="Matter QR Payload: ")
        self.printer_qrpayload_label.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        self.printer_qrpayload_data_label = tk.Label(self.printer_frame, text="-")
        self.printer_qrpayload_data_label.grid(row=3, column=2, padx=5, pady=5, sticky=tk.W)

        self.printer_manualcode_label = tk.Label(self.printer_frame, text="Matter QR Manual Code: ")
        self.printer_manualcode_label.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)

        self.printer_manualcode_data_label = tk.Label(self.printer_frame, text="-")
        self.printer_manualcode_data_label.grid(row=4, column=2, padx=5, pady=5, sticky=tk.W)

        self.printer_status_label = tk.Label(self.printer_frame, text="Print Status: ")
        self.printer_status_label.grid(row=5, column=1, padx=5, pady=5, sticky=tk.W)

        self.printer_status_data_label = tk.Label(self.printer_frame, text="-")
        self.printer_status_data_label.grid(row=5, column=2, padx=5, pady=5, sticky=tk.W)

        self.print_options_label = tk.Label(self.printer_frame, text="Print Options: ")
        self.print_options_label.grid(row=6, column=1, padx=5, pady=5, sticky=tk.W)

        self.print_option_response = tk.StringVar(value="single")

        self.print_option_response.set("double")
        self.radio_single = tk.Radiobutton(
            self.printer_frame, 
            text="Postek Single", 
            variable=self.print_option_response, 
            value="single"#,
            # command=self.print_option_response.set(value="single")
        )
        self.radio_single.grid(row=7, column=1, padx=5, pady=5, sticky=tk.W)
        # self.radio_single.pack(anchor="w") # cannot use pack as it is managed by grid

        self.radio_double = tk.Radiobutton(
            self.printer_frame, 
            text="Postek Double", 
            variable=self.print_option_response, 
            value="double"#,
            # command=self.print_option_response.set(value="double")
        )
        self.radio_double.grid(row=7, column=2, padx=5, pady=5, sticky=tk.W)
        # self.radio_double.pack(anchor="w") # cannot use pack as it is managed by grid

        self.include_sn_var = tk.BooleanVar(value=True)
        self.include_sn_checkbox = tk.Checkbutton(
            self.printer_frame, 
            text="Include Serial Number?", 
            variable=self.include_sn_var
        )
        self.include_sn_checkbox.grid(row=8, column=1, padx=5, pady=5, sticky=tk.W)

        self.printer_print = ttk.Button(self.printer_frame, text="Yes Print/打印", command=lambda: self.send_to_printer())
        self.printer_print.grid(row=9, column=1, padx=5, pady=5, sticky=tk.W)
        self.printer_print.config(state=tk.DISABLED)

        self.printer_no_print = ttk.Button(self.printer_frame, text="No Print/不打印", command=lambda: self.cancel_to_printer())
        self.printer_no_print.grid(row=9, column=2, padx=5, pady=5, sticky=tk.W)
        self.printer_no_print.config(state=tk.DISABLED)

        # Bind Enter keys to Start Button
        self.root.bind("<Return>", self.start_button_handling)

        # Bind arrow keys to scrolling
        self.root.bind("<Up>", self.scroll_vertical_up)
        self.root.bind("<Down>", self.scroll_vertical_down)
        self.root.bind("<Left>", self.scroll_horizontal_left)
        self.root.bind("<Right>", self.scroll_horizontal_right)

        # Bind space and Escape to yes no button
        self.root.bind("<space>", self.yes_buttons_handling)
        self.root.bind("<Escape>", self.no_buttons_handling)

        # Bind Ctrl + C to the handler
        self.root.bind("<Control-c>", self.handle_ctrl_c)

        # Bind Ctrl + Alt + r to the handler
        self.root.bind("<Control-Alt-r>", self.handle_ctrl_alt_r)

        # Bind Ctrl + 1 to the handler
        self.root.bind("<Control-Key-1>", self.start_button_handling)

        # Bind Ctrl + 2 to the handler
        self.root.bind("<Control-Key-2>", self.flash_button_handling)

        # Bind Ctrl + 3 to the handler
        self.root.bind("<Control-Key-3>", self.retest_button_handling)

        # Bind Ctrl + 4 to the handler
        self.root.bind("<Control-Key-4>", self.reload_ir_button_handling)
        
        # self.add_image_next_to_frame()
        
    # Added by Anuar    
    # Added for image testing   
    def load_image(self):
        global desired_width
        global aspect_ratio

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Determine the correct image path based on the label colors
        image_path = None
        if self.status_button_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "button.png")
        elif self.status_rgb_red_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "red.png")
        elif self.status_rgb_green_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "green.png")
        elif self.status_rgb_blue_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "blue.png")
        elif self.status_rgb_off_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "noled.png")
        elif self.ir_led1_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "ir1.png")
        elif self.ir_led2_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "ir2.png")
        elif self.ir_led3_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "ir3.png")
        elif self.ir_led4_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "ir4.png")
        elif self.ir_led5_label.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "ir5.png")
        elif self.status_short_header.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "h2header.png")
        elif self.status_h2_led_check.cget("fg") == "blue":
            image_path = os.path.join(script_dir, "images", "h2led.png")
        
        # Check if an image path was determined
        if image_path:
            if image_path in self.cached_images:
                # Use cached image to prevent blinking
                return self.cached_images[image_path]
            else:
                # Load and resize the image, keeping the aspect ratio
                try:
                    image = Image.open(image_path)
                    # Get original dimensions
                    original_width, original_height = image.size
                    
                    desired_width = 250 

                    aspect_ratio = original_height / original_width
                    new_height = int(desired_width * aspect_ratio)
                    
                    image = image.resize((desired_width, new_height), Image.Resampling.LANCZOS)
                    self.cached_images[image_path] = ImageTk.PhotoImage(image)
                    return self.cached_images[image_path]
                except Exception as e:
                    print(f"Error loading image: {e}")
                    return None
        else:
            print("No label is blue, cannot load image.")
            return None


    def add_image_next_to_frame(self):
        # Load the image
        image = self.load_image()
        
        # Create a frame for the image next to group3_frame
        image_frame = tk.Frame(self.scrollable_frame)
        image_frame.grid(row=10, column=0, padx=10, pady=10, sticky=tk.W)
        
        # Add the image to a label and place it in image_frame
        image_label = tk.Label(image_frame, image=image)
        image_label.image = image  # Keep a reference to avoid garbage collection
        image_label.pack()
        
    def clear_image_label(self):
        global desired_width
        global aspect_ratio

        # Clear the image label by setting it to an empty image

        new_height = int(desired_width * aspect_ratio)
        
        empty_image = Image.new('RGB', (desired_width, new_height), (217, 217, 217))  # Create a blank image with color #D9D9D9
        empty_photo = ImageTk.PhotoImage(empty_image)
        
        # Create a frame for the image next to group3_frame
        image_frame = tk.Frame(self.scrollable_frame)
        image_frame.grid(row=10, column=0, padx=10, pady=10, sticky=tk.W)
        
        # Add the empty image to a label and place it in image_frame
        image_label = tk.Label(image_frame, image=empty_photo)
        image_label.image = empty_photo  # Keep a reference to avoid garbage collection
        image_label.pack()
    
    def button_fail(self):
        print("Button Failed")
        self.result_button_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.button_fail_button.config(state=tk.DISABLED)

    # Function: handle_exit_correctly
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def handle_exit_correctly(self):
        global check_esp32s3_module
        global yes_no_button_handling_sequence

        check_esp32s3_module = 0
        yes_no_button_handling_sequence = 0

        logging.shutdown()

        logger.info("close_serial_port")
        # self.datadog_logging("info", "close_serial_port")
        self.datadog_logging(
            "info",
            {
                "summary": "close_serial_port"
            }
        )
        print("close_serial_port")
        self.close_serial_port()

        # self.task1_completed.set()
        self.task1_thread_failed.set()
        self.task2_thread_failed.set()
        
        # self.fail_ui()
        # self.stop_event.set()
        self.enable_configurable_ui()

    # Define a function to handle Ctrl + C
    def handle_ctrl_c(self, event):
        # self.handle_exit_correctly()
        # messagebox.showwarning("Warning", "Forced Stop!")
        self.stop_event.set()  # Signal the threads to stop

    # Define a function to handle Ctrl + r
    def handle_ctrl_alt_r(self, event):
        answer = messagebox.askyesno("Reboot Confirmation", "Are you sure you want to reboot?")
        if answer:
            os.system("sudo reboot")

    # Function for handling start button binding
    def start_button_handling(self, event):
        state = self.start_button.cget("state")
        # print(f"{state}")
        if f"{state}" == "normal":
            # print("here")
            self.start_button.invoke()

    # Function for handling flash button binding
    def flash_button_handling(self, event):
        state = self.flash_button.cget("state")
        # print(f"{state}")
        if f"{state}" == "normal":
            # print("here")
            self.flash_button.invoke()

    # Function for handling retest button binding
    def retest_button_handling(self, event):
        state = self.retest_button.cget("state")
        # print(f"{state}")
        if f"{state}" == "normal":
            # print("here")
            self.retest_button.invoke()

    # Function for handling reload ir button binding
    def reload_ir_button_handling(self, event):
        state = self.reload_ir_button.cget("state")
        # print(f"{state}")
        if f"{state}" == "normal":
            # print("here")
            self.reload_ir_button.invoke()

    # Function for handling all yes buttons
    def yes_buttons_handling(self, event):
        global yes_no_button_handling_sequence
        
        state = ""

        match yes_no_button_handling_sequence:
            case 0:
                pass
            case 1:
                state = self.yes_button_red.cget("state")
                if f"{state}" == "normal":
                    self.yes_button_red.invoke()
            case 2:
                state = self.yes_button_green.cget("state")
                if f"{state}" == "normal":
                    self.yes_button_green.invoke()
            case 3:
                state = self.yes_button_blue.cget("state")
                if f"{state}" == "normal":
                    self.yes_button_blue.invoke()
            case 4:
                state = self.yes_button_rgb_off.cget("state")
                if f"{state}" == "normal":
                    self.yes_button_rgb_off.invoke()
            case 5:
                state = self.yes_button_ir_led1.cget("state")
                if f"{state}" == "normal":
                    self.yes_button_ir_led1.invoke()
            case 6:
                state = self.yes_button_ir_led2.cget("state")
                if f"{state}" == "normal":
                    self.yes_button_ir_led2.invoke()
            case 7:
                state = self.yes_button_ir_led3.cget("state")
                if f"{state}" == "normal":
                    self.yes_button_ir_led3.invoke()
            case 8:
                state = self.yes_button_ir_led4.cget("state") 
                if f"{state}" == "normal":
                    self.yes_button_ir_led4.invoke()
            case 9:
                state = self.yes_button_ir_led5.cget("state")
                if f"{state}" == "normal":
                    self.yes_button_ir_led5.invoke()
            case 10:
                state = self.yes_short_header.cget("state") 
                if f"{state}" == "normal":
                    self.yes_short_header.invoke()
            case 11:
                state = self.yes_h2_led_check.cget("state")
                if f"{state}" == "normal":
                    self.yes_h2_led_check.invoke()
            case 12:
                state = self.printer_print.cget("state")
                if f"{state}" == "normal":
                    self.printer_print.invoke()

    # Function for handling all no buttons
    def no_buttons_handling(self, event):
        global yes_no_button_handling_sequence
        
        state = ""

        match yes_no_button_handling_sequence:
            case 0:
                state = self.button_fail_button.cget("state") 
                if f"{state}" == "normal":
                    self.button_fail_button.invoke()
            case 1:
                state = self.no_button_red.cget("state") 
                if f"{state}" == "normal":
                    self.no_button_red.invoke()
            case 2:
                state = self.no_button_green.cget("state")
                if f"{state}" == "normal":
                    self.no_button_green.invoke()
            case 3:
                state = self.no_button_blue.cget("state")
                if f"{state}" == "normal":
                    self.no_button_blue.invoke()
            case 4:
                state = self.no_button_rgb_off.cget("state")
                if f"{state}" == "normal":
                    self.no_button_rgb_off.invoke()
            case 5:
                state = self.no_button_ir_led1.cget("state")
                if f"{state}" == "normal":
                    self.no_button_ir_led1.invoke()   
            case 6:
                state = self.no_button_ir_led2.cget("state")
                if f"{state}" == "normal":
                    self.no_button_ir_led2.invoke()
            case 7:
                state = self.no_button_ir_led3.cget("state")
                if f"{state}" == "normal":
                    self.no_button_ir_led3.invoke()
            case 8:
                state = self.no_button_ir_led4.cget("state")
                if f"{state}" == "normal":
                    self.no_button_ir_led4.invoke()
            case 9:
                state = self.no_button_ir_led5.cget("state")
                if f"{state}" == "normal":
                    self.no_button_ir_led5.invoke()
            case 10:
                state = self.no_short_header.cget("state")
                if f"{state}" == "normal":
                    self.no_short_header.invoke()
            case 11:
                state = self.no_h2_led_check.cget("state")
                if f"{state}" == "normal":
                    self.no_h2_led_check.invoke()
            case 12:
                state = self.printer_no_print.cget("state")
                if f"{state}" == "normal":
                    self.printer_no_print.invoke()

    # Functions for scrolling vertically and horizontally
    def scroll_vertical_up(self, event):
        self.canvas.yview_scroll(-1, "units")  # Scroll up

    def scroll_vertical_down(self, event):
        self.canvas.yview_scroll(1, "units")  # Scroll down

    def scroll_horizontal_left(self, event):
        self.canvas.xview_scroll(-1, "units")  # Scroll left

    def scroll_horizontal_right(self, event):
        self.canvas.xview_scroll(1, "units")  # Scroll right

    def update_label(self, label, text, fg, font, no_button, yes_button, color):
        label.config(text=text, fg=fg, font=font)
        # if text == "Pass":
        #     no_button.config(state='disabled')
        #     logger.info(f"{color} LED: Pass")
        #     print(f"{color} LED: Pass")

        # else:
        #     yes_button.config(state='disabled')
        #     logger.error(f"{color} LED: Failed")
        #     print(f"{color} LED: Failed")

    def update_red_label(self, text, fg, font):
        self.update_label(self.result_rgb_red_label, text, fg, font, self.no_button_red, self.yes_button_red, "Red")

    def update_green_label(self, text, fg, font):
        self.update_label(self.result_rgb_green_label, text, fg, font, self.no_button_green, self.yes_button_green, "Green")

    def update_blue_label(self, text, fg, font):
        self.update_label(self.result_rgb_blue_label, text, fg, font, self.no_button_blue, self.yes_button_blue, "Blue")

    def update_ir_rx_label(self, text, fg, font):
        self.update_label(self.result_rgb_off_label, text, fg, font, self.no_button_rgb_off, self.yes_button_rgb_off, "Off")

    def update_ir_led1_label(self, text, fg, font):
        self.update_label(self.result_ir_led1, text, fg, font, self.no_button_ir_led1, self.yes_button_ir_led1, "IR LED 1")

    def update_ir_led2_label(self, text, fg, font):
        self.update_label(self.result_ir_led2, text, fg, font, self.no_button_ir_led2, self.yes_button_ir_led2, "IR LED 2")

    def update_ir_led3_label(self, text, fg, font):
        self.update_label(self.result_ir_led3, text, fg, font, self.no_button_ir_led3, self.yes_button_ir_led3, "IR LED 3")

    def update_ir_led4_label(self, text, fg, font):
        self.update_label(self.result_ir_led4, text, fg, font, self.no_button_ir_led4, self.yes_button_ir_led4, "IR LED 4")

    def update_ir_led5_label(self, text, fg, font):
        self.update_label(self.result_ir_led5, text, fg, font, self.no_button_ir_led5, self.yes_button_ir_led5, "IR LED 5")

    def update_status_short_header_label(self, text, fg, font):
        self.update_label(self.result_short_header, text, fg, font, self.no_short_header, self.yes_short_header, "Short Header")

    def update_status_h2_led_label(self, text, fg, font):
        self.update_label(self.result_h2_led_check, text, fg, font, self.no_h2_led_check, self.yes_h2_led_check, "ESP32H2 LED")

    def enable_configurable_ui(self):
        self.start_button.config(state=tk.NORMAL)
        self.flash_button.config(state=tk.NORMAL)
        self.retest_button.config(state=tk.NORMAL)
        self.reload_ir_button.config(state=tk.NORMAL)
        self.port_dropdown.config(state=tk.NORMAL)
        self.port_dropdown1.config(state=tk.NORMAL)
        self.port_dropdown2.config(state=tk.NORMAL)
        self.port_dropdown3.config(state=tk.NORMAL)
        self.baud_dropdown.config(state=tk.NORMAL)
        self.baud_dropdown1.config(state=tk.NORMAL)
        self.baud_dropdown2.config(state=tk.NORMAL)
        self.baud_dropdown3.config(state=tk.NORMAL)

        self.refresh_com_ports_button.config(state=tk.NORMAL)
        self.check_module_button.config(state=tk.NORMAL)

        self.order_number_dropdown_list.config(state=tk.NORMAL)
        self.reload_ir_button.config(state=tk.NORMAL)
        self.refresh_order_number_button.config(state=tk.NORMAL)

        self.submit_5V_dmm.config(state=tk.DISABLED)
        self.submit_3_3V_dmm.config(state=tk.DISABLED)
        self.button_fail_button.config(state=tk.DISABLED)
        self.yes_button_red.config(state=tk.DISABLED)
        self.no_button_red.config(state=tk.DISABLED)
        self.yes_button_green.config(state=tk.DISABLED)
        self.no_button_green.config(state=tk.DISABLED)
        self.yes_button_blue.config(state=tk.DISABLED)
        self.no_button_blue.config(state=tk.DISABLED)
        self.yes_button_ir_led1.config(state=tk.DISABLED)
        self.no_button_ir_led1.config(state=tk.DISABLED)
        self.yes_button_ir_led2.config(state=tk.DISABLED)
        self.no_button_ir_led2.config(state=tk.DISABLED)
        self.yes_button_ir_led3.config(state=tk.DISABLED)
        self.no_button_ir_led3.config(state=tk.DISABLED)
        self.yes_button_ir_led4.config(state=tk.DISABLED)
        self.no_button_ir_led4.config(state=tk.DISABLED)
        self.yes_button_ir_led5.config(state=tk.DISABLED)
        self.no_button_ir_led5.config(state=tk.DISABLED)
        self.yes_short_header.config(state=tk.DISABLED)
        self.no_short_header.config(state=tk.DISABLED)
        self.yes_h2_led_check.config(state=tk.DISABLED)
        self.no_h2_led_check.config(state=tk.DISABLED)
        self.printer_print.config(state=tk.DISABLED)
        self.printer_no_print.config(state=tk.DISABLED)

    def disable_configurable_ui(self):
        self.start_button.config(state=tk.DISABLED)
        self.flash_button.config(state=tk.DISABLED)
        self.retest_button.config(state=tk.DISABLED)
        self.reload_ir_button.config(state=tk.DISABLED)
        self.port_dropdown.config(state=tk.DISABLED)
        self.port_dropdown1.config(state=tk.DISABLED)
        self.port_dropdown2.config(state=tk.DISABLED)
        self.port_dropdown3.config(state=tk.DISABLED)
        self.baud_dropdown.config(state=tk.DISABLED)
        self.baud_dropdown1.config(state=tk.DISABLED)
        self.baud_dropdown2.config(state=tk.DISABLED)
        self.baud_dropdown3.config(state=tk.DISABLED)
        
        self.refresh_order_number_button.config(state=tk.DISABLED)
        self.reload_ir_button.config(state=tk.DISABLED)

        self.refresh_com_ports_button.config(state=tk.DISABLED)
        self.check_module_button.config(state=tk.DISABLED)

        self.order_number_dropdown_list.config(state=tk.DISABLED)

        self.submit_5V_dmm.config(state=tk.DISABLED)
        self.submit_3_3V_dmm.config(state=tk.DISABLED)
        self.button_fail_button.config(state=tk.DISABLED)
        self.yes_button_red.config(state=tk.DISABLED)
        self.no_button_red.config(state=tk.DISABLED)
        self.yes_button_green.config(state=tk.DISABLED)
        self.no_button_green.config(state=tk.DISABLED)
        self.yes_button_blue.config(state=tk.DISABLED)
        self.no_button_blue.config(state=tk.DISABLED)
        self.yes_button_ir_led1.config(state=tk.DISABLED)
        self.no_button_ir_led1.config(state=tk.DISABLED)
        self.yes_button_ir_led2.config(state=tk.DISABLED)
        self.no_button_ir_led2.config(state=tk.DISABLED)
        self.yes_button_ir_led3.config(state=tk.DISABLED)
        self.no_button_ir_led3.config(state=tk.DISABLED)
        self.yes_button_ir_led4.config(state=tk.DISABLED)
        self.no_button_ir_led4.config(state=tk.DISABLED)
        self.yes_button_ir_led5.config(state=tk.DISABLED)
        self.no_button_ir_led5.config(state=tk.DISABLED)
        self.yes_short_header.config(state=tk.DISABLED)
        self.no_short_header.config(state=tk.DISABLED)
        self.yes_h2_led_check.config(state=tk.DISABLED)
        self.no_h2_led_check.config(state=tk.DISABLED)
        self.printer_print.config(state=tk.DISABLED)
        self.printer_no_print.config(state=tk.DISABLED)

    def load_test_script(self):
        ini_file_path = askopenfilename(title="Select .ini file", filetypes=[("INI files", "*.ini")])
        if not ini_file_path:
            return

        self.loadtTestScript = LoadTestScript(ini_file_path)
        with open(ini_file_path, 'r') as file:
            content = file.read()
            print(content)

    def check_factory_flag(self):
        flag_value = self.serialCom.get_factory_flag()
        print(f"Factory Flag: {flag_value}")


    # Function: start_test
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def start_test(self):
        global factory_app_version
        global device_data
        global orderNum_label
        global macAddress_label
        global serialID_label
        global certID_label
        global secureCertPartition_label
        global commissionableDataPartition_label
        global qrCode_label
        global manualCode_label
        global discriminator_label
        global passcode_label
        global orderNum_data
        global macAddress_esp32s3_data
        global serialID_data
        global certID_data
        global secureCertPartition_data
        global commissionableDataPartition_data
        global qrCode_data
        global manualCode_data
        global discriminator_data
        global passcode_data

        global ini_file_name
        global device_data_file_path
        global script_dir

        global check_esp32s3_module
        global fw_flag
        global efuse_flag

        global disable_sticker_printing

        global orderNumber

        global retest_flag
        
        global master_start_time
        
        master_start_time = datetime.now()
        
        print(f"Master Start Time: {str(master_start_time)}")
        logger.info(f"Master Start Time: {str(master_start_time)}")
        
        self.datadog_logging(
            "info",
            {
                "summary": f"Master Start Time: {str(master_start_time)}"
            }
        )

        print("Retrieve order number selected from ui")
        orderNumber = self.order_number_dropdown.get()

        # Check in the specified directory
        ini_file_path = os.path.join(script_dir, ini_file_name)

        if not os.path.exists(ini_file_path):
            logger.error(f"{ini_file_name} not found in the specified directory: {script_dir}")
            self.datadog_logging(
                "error",
                {
                        "summary": f"{ini_file_name} not found in the specified directory"
                }
            )
            return

        # Proceed to load and process the INI file
        self.loadTestScript = LoadTestScript(ini_file_path)

        config = configparser.ConfigParser()
        config.read(ini_file_path)

        esp32s3_erase_flash_enable = config.get("erase_flash_esp32s3", "erase_flash_esp32s3_enable")
        esp32s3_start_addr = config.get("erase_flash_esp32s3", "erase_flash_esp32s3_start_address")
        esp32s3_end_addr = config.get("erase_flash_esp32s3", "erase_flash_esp32s3_end_address")
        esp32h2_erase_flash_enable = config.get("erase_flash_esp32h2", "erase_flash_esp32h2_enable")
        esp32h2_start_addr = config.get("erase_flash_esp32h2", "erase_flash_esp32h2_start_address")
        esp32h2_end_addr = config.get("erase_flash_esp32h2", "erase_flash_esp32h2_end_address")

        esp32s3_port = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_port")
        esp32s3_baud = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_baud")
        esp32s3_bootloader_address = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_bootloader_address")
        esp32s3_partition_table_address = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_partition_table_address")
        esp32s3_ota_data_initial_address = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_ota_data_initial_address")
        esp32s3_fw_address = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_address")
        esp32s3_use_esptool = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_use_esptool")
        esp32s3_not_encrypted = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_not_encrypted")
        esp32s3_fw_filename = config.get("flash_firmware_esp32s3", "flash_firmware_esp32s3_filename")
        bypass_efuse_check = config.get("flash_firmware_esp32s3", "bypass_efuse_check")

        print("")
        print("")
        print(f"testscript.ini configuration: esp32s3_not_encrypted = {esp32s3_not_encrypted}")
        print("")
        print("")

        # esp32s3_port = "/dev/ttyACM0"
        esp32s3_port = self.port_var.get()
        esp32s3_baud = int(self.baud_var.get())

        esp32s3_factory_port = self.port_var1.get()
        esp32s3_factory_baud = int(self.baud_var1.get())

        esp32h2_port = config.get("flash_firmware_esp32h2", "flash_firmware_esp32h2_port")
        esp32h2_baud = config.get("flash_firmware_esp32h2", "flash_firmware_esp32h2_baud")
        esp32h2_bootloader_address = config.get("flash_firmware_esp32h2", "flash_firmware_esp32h2_bootloader_address")
        esp32h2_partition_table_address = config.get("flash_firmware_esp32h2", "flash_firmware_esp32h2_partition_table_address")
        esp32h2_fw_address = config.get("flash_firmware_esp32h2", "flash_firmware_esp32h2_address")
        esp32h2_use_esptool = config.get("flash_firmware_esp32h2", "flash_firmware_esp32h2_use_esptool")
        esp32h2_fw_filename = config.get("flash_firmware_esp32h2", "flash_firmware_esp32h2_filename")

        esp32h2_port = self.port_var2.get()
        esp32h2_baud = int(self.baud_var2.get())

        esp32s3_module_port = self.port_var3.get()
        esp32s3_module_baud = int(self.baud_var3.get())

        esp32s3_securecert_partition = config.get("flash_dac_esp32s3", "flash_dac_esp32s3_secure_cert_partition")
        esp32s3_data_provider_partition = config.get("flash_dac_esp32s3", "flash_dac_esp32s3_data_provider_partition")
        esp32s3_dac_use_esptool = config.get("flash_dac_esp32s3", "flash_dac_esp32s3_use_esptool")
        esp32s3_dac_production_mode = config.get("flash_dac_esp32s3", "flash_dac_esp32s3_production_mode")

        if f"{orderNumber}" == "hand-sample" or f"{orderNumber}" == "200-trial-run":
            esp32s3_dac_production_mode = "False"
        else:
            esp32s3_dac_production_mode = "True"

        print("")
        print("")
        print(f"final configuration: esp32s3_dac_production_mode = {esp32s3_dac_production_mode} !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("")
        print("")

        esp32s3_dac_folder_name = config.get("flash_dac_esp32s3", "flash_dac_esp32s3_folder_name")

        esp32s3_factory_reset_command = config.get("factory_reset", "factory_reset_command")

        # with concurrent.futures.ThreadPoolExecutor() as executor:
        #     future_s3 = executor.submit(self.read_s3_mac_address, esp32s3_port, esp32s3_baud)
        #     future_h2 = executor.submit(self.read_h2_mac_address, esp32h2_port, esp32h2_baud)

        #     # Wait for both futures to complete
        #     concurrent.futures.wait([future_s3, future_h2])
        
        #****************************************************************************************#
        # Add new flow of checking the FW availability
        # Open Port --> Reset Device
        
        # 1. Move eFuse Check after firmware check -Done
        # 2. Change Burned to Fail
        # 3. If Device Not Flashed & Burned = Stop Test
        # 4. If Device Flashed & Burned / Not Burned = Continue Test

        self.status_fw_availability_label.config(fg="blue")
        self.status_fw_availability_label.grid()
        
        print("Start Checking FW ESP32S3")

        print("Reset Firmware Availability Flag")
        self.serialCom.reset_fw_availability_flag()

        fw_flag = self.serialCom.get_fw_availability_flag()

        print(f"FW Flag: {fw_flag}")
        logger.info(f"FW Flag: {fw_flag}")

        print("Open esp32s3 Factory Port")
        print(f"factory Port: {esp32s3_factory_port}, Baud: {esp32s3_factory_baud}")
        if self.serialCom.open_serial_port(esp32s3_factory_port, esp32s3_factory_baud):
            self.handle_exit_correctly()
            print("Failed to open esp32s3 factory port")
            messagebox.showerror("Error", "Failed to open esp32s3 factory port")
            return True

        print(f"Reboot esp32s3, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
        self.reboot_s3(False, True, esp32s3_port, esp32s3_baud)

        logger.info("Start Wait 3")
        print("Start Wait 3")
        time.sleep(3)
        logger.info("Finish Wait 3")
        print("Finish Wait 3")

        if f"{orderNumber}" == "hand-sample" or f"{orderNumber}" == "200-trial-run":
            esp32s3_not_encrypted = "True"
        else:
            esp32s3_not_encrypted = "False"

        print("")
        print("")
        print(f"final configuration: esp32s3_not_encrypted = {esp32s3_not_encrypted} !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("")
        print("")

        logger.info("Retrieve ESP32S3 MAC Address")
        # self.datadog_logging(
        #     "info",
        #     {
        #             "summary": "Retrieve ESP32S3 MAC Address"
        #         }
        # )
        print("Retrieve ESP32S3 MAC Address")
        esp32s3_mac_add = self.flashFw.retrieve_esp32s3_mac_address()

        print("Retrieve device data")
        device_data = self.retrieve_device_data(str(device_data_file_path), str(orderNumber), str(esp32s3_mac_add))
        if device_data == "":
            self.handle_exit_correctly()
            print("No available data")
            self.datadog_logging(
                "error",
                {
                        "summary": "No data available in database"
                }
            )
            messagebox.showerror("Error", "No data available in database")
            return True
        else:
            pass

        print("Parse device data")
        self.parse_device_data(str(device_data), str(esp32s3_mac_add))

        print("Initialize logging")
        if self.initialize_logging(str(esp32s3_mac_add), str(serialID_data)) == True:
            self.handle_exit_correctly()
            print("Fail to initialize logging")
            messagebox.showerror("Error", "Fail to initialize logging")
            return True
        else:
            pass

        fw_flag = self.serialCom.get_fw_availability_flag()

        print(f"FW Flag: {fw_flag}")
        logger.info(f"FW Flag: {fw_flag}")

        if fw_flag == True:
            logger.info("Firmware Available")
            self.datadog_logging(
                "info",
                {
                        "summary": "Firmware Available"
                    }
            )
            print("Firmware Available")
            self.fw_availability_label.config(text="Firmware Available", fg="black", font=("Helvetica", 10, "bold"))

            logger.info("Reset Firmware Availability Flag")
            self.datadog_logging(
                "info",
                {
                        "summary": "Reset Firmware Availability Flag"
                }
            )
            print("Reset Firmware Availability Flag")
            self.serialCom.reset_fw_availability_flag()

            # If firmware is available then need to execute factory reset to remove all previous settings

            self.send_command(esp32s3_factory_reset_command + "\r\n")
            start_time = time.time()
            # while time.time() - start_time < float(20):
            while True:
                fw_flag = self.serialCom.get_fw_availability_flag()
                # print(f"Factory Reset Flag: {fw_flag}")
                if fw_flag == True:
                    logger.info("Factory Reset Success")
                    print("Factory Reset Success")
                    break
                else:
                    logger.info("Factory Reset Failed")
                    print("Factory Reset Failed")
                    if ((time.time() - start_time) > float(30)):
                        self.handle_exit_correctly()
                        messagebox.showerror("Error", "Factory Reset Failed")
                        break
                time.sleep(1)
        else:
            # log_header = self.device_info
            logger.info("No Firmware")
            self.datadog_logging(
                "info",
                {
                        "summary": "No Firmware"
                }
            )
            print("No Firmware")
            self.fw_availability_label.config(text="No Firmware", fg="black", font=("Helvetica", 10, "bold"))
                
        # if fw_flag == True and esp32s3_not_encrypted == "False":
        #     logger.info("Device Already Flashed")
        #     print("Device Already Flashed")
        #     self.fw_availability_label.config(text="Device Flashed", fg="black", font=("Helvetica", 10, "bold"))
            
        #     print("Start Checking eFuse ESP32S3")
        #     self.s3_espfuse(esp32s3_port)
            
        # elif fw_flag == True and esp32s3_not_encrypted == "True":
        #     logger.info("Device Already Flashed")
        #     print("Device Already Flashed")
        #     self.fw_availability_label.config(text="Device Flashed", fg="black", font=("Helvetica", 10, "bold"))
        
        # elif fw_flag == False:
        #     logger.error("Device Not Yet Flashed")
        #     print("Device Not Yet Flashed")
        #     self.fw_availability_label.config(text="Device Not Flashed", fg="black", font=("Helvetica", 10, "bold"))
                        
        # else:
        #     logger.error("Device Not Yet Flashed")
        #     print("Device Not Yet Flashed")
        #     self.fw_availability_label.config(text="Device Not Flashed", fg="black", font=("Helvetica", 10, "bold"))
        
        # self.handle_exit_correctly()
        # messagebox.showerror("Error", "Test Stop!")
        # return True

        self.datadog_logging(
            "info",
            {
                "summary": "close_serial_port"
            }
        )
        logger.info("close_serial_port")
        print("close_serial_port")
        self.close_serial_port()

        self.status_fw_availability_label.config(fg="black")
        self.status_fw_availability_label.grid()

        self.status_espfuse_s3.config(fg="blue")
        self.status_espfuse_s3.grid()

        if esp32s3_not_encrypted == "True":
        # if f"{orderNumber}" == "hand-sample" or f"{orderNumber}" == "200-trial-run":
            logger.info("Skip Checking eFuse ESP32S3 due to select 'hand-sample' and '200-trial-run' order number")
            print("Skip Checking eFuse ESP32S3 due to select 'hand-sample' and '200-trial-run' order number")
            self.result_espfuse_s3.config(text="SKIP", fg="black", font=("Helvetica", 10, "bold"))
        else:
            logger.info("Start Checking eFuse ESP32S3")
            print("Start Checking eFuse ESP32S3") 
            self.s3_espfuse(esp32s3_port, fw_flag) #this will have a short term fail indication in the event burn fuse have been done

            if bypass_efuse_check == "False":
                if fw_flag == True:
                    logger.info("Completed Checking eFuse ESP32S3 due firmware available")
                    print("Completed Checking eFuse ESP32S3 due firmware available")
                    self.result_espfuse_s3.config(text="Completed", fg="green", font=("Helvetica", 10, "bold"))
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Completed Checking eFuse ESP32S3"
                        }
                    ) 
                else:
                    if self.result_espfuse_s3.cget("text") == "Failed":
                        # self.handle_exit_correctly() #comment out to remove the restriction but will capture this as a warning, probably previously fail flash firmware, 20241210 by soo
                        logger.info("ESP32S3 eFuse Failed/Already Burned")
                        self.datadog_logging(
                            "warning",
                            {
                                    "summary": "ESP32S3 eFuse Failed/Already Burned"
                            }
                        )
                        print("ESP32S3 eFuse Failed/Already Burned")
                        messagebox.showwarning("Warning", "ESP32S3 eFuse Failed/Already Burned. You may ignore this!")
                        # messagebox.showerror("Error", "ESP32S3 eFuse Failed/Already Burned. Please discard the board.") #comment out to remove the restriction but will capture this as a warning, probably previously fail flash firmware, 20241210 by soo
                        # return True #comment out to remove the restriction but will capture this as a warning, probably previously fail flash firmware, 20241210 by soo
                    else:
                        logger.info("Completed Checking eFuse ESP32S3 due executed burn efuse")
                        print("Completed Checking eFuse ESP32S3 due executed burn efuse")
                        self.result_espfuse_s3.config(text="Completed", fg="green", font=("Helvetica", 10, "bold"))
                        self.datadog_logging(
                            "info",
                            {
                                    "summary": "Completed Checking eFuse ESP32S3"
                            }
                        )  
            else:
                logger.info("Skip Checking eFuse ESP32S3 due to bypass efuse")
                print("Skip Checking eFuse ESP32S3 due to bypass efuse")
                self.result_espfuse_s3.config(text="SKIP", fg="black", font=("Helvetica", 10, "bold"))
                self.datadog_logging(
                    "info",
                    {
                            "summary": "Skip Checking eFuse ESP32S3"
                    }
                )           
            
        self.status_espfuse_s3.config(fg="black")
        self.status_espfuse_s3.grid()

        # self.handle_exit_correctly()
        # messagebox.showerror("Error", "Test Stop!")
        # return True

        #****************************************************************************************#

        self.read_mac_address_label.config(fg="blue")
        self.read_mac_address_label.grid()

        print("Read ESP32S3 MAC Address")
        if check_esp32s3_module == 1:
            self.read_s3_mac_address(esp32s3_module_port, esp32s3_module_baud)
        else:
            self.read_s3_mac_address(esp32s3_port, esp32s3_baud)

        # print("System Sleep")
        # time.sleep(5)

        logger.info("Retrieve ESP32S3 MAC Address")
        self.datadog_logging(
            "info",
            {
                    "summary": "Retrieve ESP32S3 MAC Address"
                }
        )
        print("Retrieve ESP32S3 MAC Address")
        esp32s3_mac_add = self.flashFw.retrieve_esp32s3_mac_address()
        if esp32s3_mac_add == "":
            self.handle_exit_correctly()
            print("Fail to get ESP32S3 MAC Address")
            messagebox.showerror("Error", "Fail to get ESP32S3 MAC Address")
            return True
        else:
            print(f"ESP32S3 MAC Address: {esp32s3_mac_add}")

        logger.info(f"Factory App Version: {factory_app_version}")
        self.datadog_logging(
            "info",
            {
                    "summary": f"Factory App Version: {factory_app_version}"
            }
        )
        print(f"Factory App Version: {factory_app_version}")
        logger.info("Test 1 Start")
        self.datadog_logging(
            "info",
            {
                    "summary": "Test 1 Start"
            }
        )
        print("Test 1 Start")
        logger.info(f"Below are information extracted based on ESP32S3 MAC Address")
        logger.info(f"{orderNum_label}: {orderNum_data}")
        logger.info(f"{macAddress_label}: {macAddress_esp32s3_data}")
        logger.info(f"{serialID_label}: {serialID_data}")
        logger.info(f"{certID_label}: {certID_data}")
        logger.info(f"{secureCertPartition_label}: {secureCertPartition_data}")
        logger.info(f"{commissionableDataPartition_label}: {commissionableDataPartition_data}")
        logger.info(f"{qrCode_label}: {qrCode_data}")
        logger.info(f"{manualCode_label}: {manualCode_data}")
        logger.info(f"{discriminator_label}: {discriminator_data}")
        logger.info(f"{passcode_label}: {passcode_data}")
        
        self.datadog_logging(
            "info",
            f"Test 1 Start ,"
            f"{orderNum_label}: {orderNum_data},"
            f"{macAddress_label}: {macAddress_esp32s3_data},"
            f"{serialID_label}: {serialID_data},"
            f"{certID_label}: {certID_data},"
            f"{secureCertPartition_label}: {secureCertPartition_data},"
            f"{commissionableDataPartition_label}: {commissionableDataPartition_data},"
            f"{qrCode_label}: {qrCode_data},"
            f"{manualCode_label}: {manualCode_data},"
            f"{discriminator_label}: {discriminator_data},"
            f"{passcode_label}: {passcode_data}"
        )

        print(f"Below are information extracted based on ESP32S3 MAC Address")
        print(f"{orderNum_label}: {orderNum_data}")
        print(f"{macAddress_label}: {macAddress_esp32s3_data}")
        print(f"{serialID_label}: {serialID_data}")
        print(f"{certID_label}: {certID_data}")
        print(f"{secureCertPartition_label}: {secureCertPartition_data}")
        print(f"{commissionableDataPartition_label}: {commissionableDataPartition_data}")
        print(f"{qrCode_label}: {qrCode_data}")
        print(f"{manualCode_label}: {manualCode_data}")
        print(f"{discriminator_label}: {discriminator_data}")
        print(f"{passcode_label}: {passcode_data}")
        
        # self.datadog_logging("info","Read ESP32S3 MAC Address")
        self.datadog_logging(
            "info",
            {
                    "summary": "Read ESP32S3 MAC Address"
            }
        )

        logger.info("Read ESP32S3 Mac Address")
        print("Read ESP32S3 Mac Address")
        # self.record_s3_mac_address(macAddress_esp32s3_data)
        if self.result_mac_address_s3_label.cget("text") == "Not Yet":
            self.result_mac_address_s3_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        else:
            pass

        if check_esp32s3_module == 1:
            pass
        else:
            # self.datadog_logging("info","Read ESP32H2 MAC Address")
            self.datadog_logging(
                "info",
                {
                        "summary": "Read ESP32H2 MAC Address"
                }
            )
            logger.info("Read ESP32H2 MAC Address")
            print("Read ESP32H2 MAC Address")
            self.read_h2_mac_address(esp32h2_port, esp32h2_baud)
            if self.result_mac_address_h2_label.cget("text") == "Not Yet":
                self.result_mac_address_h2_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                self.handle_exit_correctly()
                logger.info("Failed to read ESP32H2 MAC Address")
                # self.datadog_logging("error","Failed to read ESP32H2 MAC Address")
                self.datadog_logging(
                    "error",
                    {
                            "summary": "Failed to read ESP32H2 MAC Address"
                    }
                )
                print("Failed to read ESP32H2 MAC Address")
                messagebox.showerror("Error", "Fail to read ESP32H2 MAC Address, Please make sure the port is correct.")
                return True
            
            else:
                pass

        self.read_mac_address_label.config(fg="black")
        self.read_mac_address_label.grid()

        if retest_flag == 0:
            self.status_flashing_fw.config(fg="blue")
            self.status_flashing_fw.grid()
            
            test_start_time = datetime.now()
            logger.info(f"Start Time ESP32S3: {test_start_time}")

            # if "flash" in config:
            #     logger.info("Flashing firmware and certificate")
            #     port = config.get("flash", "port")
            #     baud = config.get("flash", "baud")
            #     logger.info(f"Port: {port}, Baud: {baud}")
            #     self.flashFw.export_esp_idf_path()
            #     self.flash_s3_firmware(port, baud)
                # self.flash_cert(port)

            # if "flash_firmware_esp32s3" in config:
            if check_esp32s3_module == 1:
                logger.info(f"Flashing ESP32S3 Module firmware, Port: {esp32s3_module_port}, Baud: {esp32s3_module_baud}")

                print(f"Flashing ESP32S3 Module firmware, Port: {esp32s3_module_port}, Baud: {esp32s3_module_baud}")
                
                # self.datadog_logging("info","Flashing ESP32S3 Module firmware, Port: {esp32s3_module_port}, Baud: {esp32s3_module_baud}")
                
                self.datadog_logging(
                    "info",
                    {
                            "summary": f"Flashing ESP32S3 Module firmware, Port: {esp32s3_module_port}, Baud: {esp32s3_module_baud}"
                    }
                )
                
                

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future_flash_s3 = executor.submit(self.flash_s3_firmware, 
                                                    esp32s3_use_esptool, 
                                                    esp32s3_not_encrypted, 
                                                    True, 
                                                    esp32s3_module_port, 
                                                    esp32s3_module_baud, 
                                                    esp32s3_bootloader_address, 
                                                    esp32s3_partition_table_address, 
                                                    esp32s3_ota_data_initial_address, 
                                                    esp32s3_fw_address, 
                                                    esp32s3_fw_filename
                                                    )
                    
                    future_flash_h2 = executor.submit(None)

                    # Wait for both futures to complete
                    concurrent.futures.wait([future_flash_s3, future_flash_h2])

                time.sleep(1)
            else:
                logger.info("Flashing esp32s3 and esp32h2 firmware")
                self.datadog_logging(
                    "info",
                    {
                            "summary": "Flashing esp32s3 and esp32h2 firmware"
                    }
                )
                
                print("Flashing esp32s3 and esp32h2 firmware")

                logger.info(f"Erase Flash ESP32S3: {esp32s3_erase_flash_enable}")
                logger.info(f"Erase Flash ESP32S3 Start Address: {esp32s3_start_addr}")
                logger.info(f"Erase Flash ESP32S3 End Address: {esp32s3_end_addr}")
                
                self.datadog_logging(
                    "info",
                    {
                            "summary": f"Erase Flash ESP32S3: {esp32s3_erase_flash_enable}",
                            "item": "Erase Flash ESP32S3",
                            "details": {
                                "Start Address": esp32s3_start_addr,
                                "End Address": esp32s3_end_addr
                        }
                    }
                )

                logger.info(f"Erase Flash ESP32H2: {esp32h2_erase_flash_enable}")
                logger.info(f"Erase Flash ESP32H2 Start Address: {esp32h2_start_addr}")
                logger.info(f"Erase Flash ESP32H2 End Address: {esp32h2_end_addr}")
                
                self.datadog_logging(
                    "info",
                    {
                            "summary": f"Erase Flash ESP32H2: {esp32h2_erase_flash_enable}",
                            "item": "Erase Flash ESP32H2",
                            "details": {
                                "Start Address": esp32h2_start_addr,
                                "End Address": esp32h2_end_addr
                            }
                    }
                )

                print(f"Erase Flash ESP32S3: {esp32s3_erase_flash_enable}")
                print(f"Erase Flash ESP32S3 Start Address: {esp32s3_start_addr}")
                print(f"Erase Flash ESP32S3 End Address: {esp32s3_end_addr}")

                print(f"Erase Flash ESP32H2: {esp32h2_erase_flash_enable}")
                print(f"Erase Flash ESP32H2 Start Address: {esp32h2_start_addr}")
                print(f"Erase Flash ESP32H2 End Address: {esp32h2_end_addr}")

                logger.info(f"Flashing ESP32S3 firmware, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
                logger.info(f"ESP32S3 Bootloader Address: {esp32s3_bootloader_address}")
                logger.info(f"ESP32S3 Partition Table Address: {esp32s3_partition_table_address}")
                logger.info(f"ESP32S3 OTA Data Initial Address: {esp32s3_ota_data_initial_address}")
                logger.info(f"ESP32S3 Firmware Address: {esp32s3_fw_address}")
                logger.info(f"ESP32S3 Use ESPTOOL: {esp32s3_use_esptool}")
                logger.info(f"ESP32S3 Not Encrypted: {esp32s3_not_encrypted}")
                logger.info(f"ESP32S3 Firmware Filename: {esp32s3_fw_filename}")
                
                # self.datadog_logging("info","Flashing ESP32S3 firmware, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
                
                self.datadog_logging(
                    "info",
                    {
                            "summary": f"Start: Flashing ESP32S3 firmware",
                            "item": "Flashing ESP32S3 firmware",
                            "details": {
                                "Action": "Flashing ESP32S3 firmware",
                                "Port": esp32s3_port,
                                "Baud": esp32s3_baud,
                                "Bootloader Address": esp32s3_bootloader_address,
                                "Partition Table Address": esp32s3_partition_table_address,
                                "OTA Data Initial Address": esp32s3_ota_data_initial_address,
                                "ESPTool": esp32s3_use_esptool,
                                "Status": esp32s3_not_encrypted,
                                "Firmware Filename": esp32s3_fw_filename
                            }
                        }
                )
                

                print(f"Flashing ESP32S3 firmware, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
                print(f"ESP32S3 Bootloader Address: {esp32s3_bootloader_address}")
                print(f"ESP32S3 Partition Table Address: {esp32s3_partition_table_address}")
                print(f"ESP32S3 OTA Data Initial Address: {esp32s3_ota_data_initial_address}")
                print(f"ESP32S3 Firmware Address: {esp32s3_fw_address}")
                print(f"ESP32S3 Use ESPTOOL: {esp32s3_use_esptool}")
                print(f"ESP32S3 Not Encrypted: {esp32s3_not_encrypted}")
                print(f"ESP32S3 Firmware Filename: {esp32s3_fw_filename}")

                logger.info(f"Flashing ESP32H2 firmware, Port: {esp32h2_port}, Baud: {esp32h2_baud}")
                logger.info(f"ESP32H2 Bootloader Address: {esp32h2_bootloader_address}")
                logger.info(f"ESP32H2 Partition Table Address: {esp32h2_partition_table_address}")
                logger.info(f"ESP32H2 Firmware Address: {esp32h2_fw_address}")
                logger.info(f"ESP32H2 Use ESPTOOL: {esp32h2_use_esptool}")
                logger.info(f"ESP32H2 Firmware Filename: {esp32h2_fw_filename}")
                
                # self.datadog_logging("info","Flashing ESP32H2 firmware, Port: {esp32h2_port}, Baud: {esp32h2_baud}")
                self.datadog_logging(
                    "info",
                    {
                            "summary": f"Start: Flashing ESP32H2 firmware", 
                            "item": "Flashing ESP32H2 firmware",
                            "details": {
                                "Action": "Flashing ESP32H2 firmware",
                                "Port": esp32h2_port,
                                "Baud": esp32h2_baud,
                                "Bootloader Address": esp32h2_bootloader_address,
                                "Partition Table Address": esp32h2_partition_table_address,
                                "ESPTool": esp32h2_use_esptool,
                                "Firmware Filename": esp32h2_fw_filename
                            }
                    }
                )

                print(f"Flashing ESP32H2 firmware, Port: {esp32h2_port}, Baud: {esp32h2_baud}")
                print(f"ESP32H2 Bootloader Address: {esp32h2_bootloader_address}")
                print(f"ESP32H2 Partition Table Address: {esp32h2_partition_table_address}")
                print(f"ESP32H2 Firmware Address: {esp32h2_fw_address}")
                print(f"ESP32H2 Use ESPTOOL: {esp32h2_use_esptool}")
                print(f"ESP32H2 Firmware Filename: {esp32h2_fw_filename}")

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future_erase_s3 = executor.submit(self.erase_flash_esp32s3, 
                                                    esp32s3_erase_flash_enable, 
                                                    esp32s3_use_esptool, 
                                                    esp32s3_not_encrypted, 
                                                    esp32s3_port, 
                                                    esp32s3_baud, 
                                                    esp32s3_start_addr, 
                                                    esp32s3_end_addr
                                                    )
                    
                    future_erase_h2 = executor.submit(self.erase_flash_esp32h2, 
                                                    esp32h2_erase_flash_enable, 
                                                    esp32h2_use_esptool, 
                                                    esp32h2_port, 
                                                    esp32h2_baud, 
                                                    esp32h2_start_addr, 
                                                    esp32h2_end_addr
                                                    )

                    # Wait for both futures to complete
                    concurrent.futures.wait([future_erase_s3, future_erase_h2])

                time.sleep(1)

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future_flash_s3 = executor.submit(self.flash_s3_firmware, 
                                                    esp32s3_use_esptool, 
                                                    esp32s3_not_encrypted, 
                                                    False, 
                                                    esp32s3_port, 
                                                    esp32s3_baud, 
                                                    esp32s3_bootloader_address, 
                                                    esp32s3_partition_table_address, 
                                                    esp32s3_ota_data_initial_address, 
                                                    esp32s3_fw_address, 
                                                    esp32s3_fw_filename
                                                    )
                    
                    future_flash_h2 = executor.submit(self.flash_h2_firmware, 
                                                    esp32h2_use_esptool, 
                                                    esp32h2_port, 
                                                    esp32h2_baud, 
                                                    esp32h2_bootloader_address, 
                                                    esp32h2_partition_table_address, 
                                                    esp32h2_fw_address, 
                                                    esp32h2_fw_filename
                                                    )

                    # Wait for both futures to complete
                    concurrent.futures.wait([future_flash_s3, future_flash_h2])

                time.sleep(1)

            if self.result_flashing_fw_label.cget("text") == "Not Yet" or self.result_flashing_fw_label.cget("text") != "Completed":
                self.result_flashing_fw_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                self.handle_exit_correctly()
                # self.datadog_logging("error","Failed to flash ESP32S3 Firmware")
                self.datadog_logging(
                    "error",
                    {
                            "summary": "Failed to flash ESP32S3 Firmware"
                        }
                )
                logger.info("Failed to flash ESP32S3 Firmware")
                print("Failed to flash ESP32S3 Firmware")
                messagebox.showerror("Error", "Fail to flash ESP32S3 Firmware, Please make sure the port is correct.")
                return True        
            else:
                pass

            if check_esp32s3_module == 1:
                pass
            else:
                if self.result_flashing_fw_h2_label.cget("text") == "Not Yet" or self.result_flashing_fw_h2_label.cget("text") != "Completed":
                    self.result_flashing_fw_h2_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                    self.handle_exit_correctly()
                    # self.datadog_logging("error","Failed to flash ESP32H2 Firmware")
                    self.datadog_logging(
                        "error",
                        {
                                "summary": "Failed to flash ESP32H2 Firmware"
                        }
                    )
                    logger.info("Failed to flash ESP32H2 Firmware")
                    print("Failed to flash ESP32H2 Firmware")
                    messagebox.showerror("Error", "Fail to flash ESP32H2 Firmware, Please make sure the port is correct.")
                    return True
                
                else:
                    pass
            
            self.datadog_logging(
                "info" if self.result_flashing_fw_label.cget("text") == "Completed" else "error",
                {
                        "summary": "End: Flashing ESP32S3 firmware",
                        "item": "Flashing ESP32S3 firmware",
                        "details": {
                            "Result": "Completed" if self.result_flashing_fw_label.cget("text") == "Completed" else "Failed"
                        }
                }
            )

            self.datadog_logging(
                "info" if self.result_flashing_fw_h2_label.cget("text") == "Completed" else "error",
                {
                        "summary": "End: Flashing ESP32H2 firmware",
                        "item": "Flashing ESP32H2 firmware",
                        "details": {
                            "Result": "Completed" if self.result_flashing_fw_h2_label.cget("text") == "Completed" else "Failed"
                        }
                }
            )
            
            end_time = datetime.now()
            
            duration = end_time - test_start_time
            
            logger.info(f"End Time ESP32S3: {end_time}")
            
            logger.info(f"Duration ESP32S3: {duration}")
            
            self.datadog_logging(
                "info" if self.result_flashing_fw_label.cget("text") == "Completed" else "error" or "info" if self.result_flashing_fw_h2_label.cget("text") == "Completed" else "error",
                {
                        "summary": "End: Flashing ESP32S3 and ESP32H2 firmware",
                        "item": "Flashing ESP32S3 and ESP32H2 firmware",
                        "start_time": str(test_start_time),
                        "end_time": str(end_time),
                        "duration": str(duration),
                        "details": {
                            "Result": "Completed" if self.result_flashing_fw_label.cget("text") == "Completed" and self.result_flashing_fw_h2_label.cget("text") == "Completed" else "Failed"
                        }
                }
            )
                

            self.status_flashing_fw.config(fg="black")
            self.status_flashing_fw.grid()
        else:
            logger.info("Skip Flashing ESP32S3 and ESP32H2 firmware")
            print("Skip Flashing ESP32S3 and ESP32H2 firmware")

            self.result_flashing_fw_label.config(text="SKIP", fg="black", font=("Helvetica", 10, "bold"))
            self.result_flashing_fw_label.grid()
            self.result_flashing_fw_h2_label.config(text="SKIP", fg="black", font=("Helvetica", 10, "bold"))
            self.result_flashing_fw_h2_label.grid()

            self.datadog_logging(
                "info" if self.result_flashing_fw_label.cget("text") == "Completed" else "error",
                {
                        "summary": "End: Flashing ESP32S3 firmware",
                        "item": "Flashing ESP32S3 firmware",
                        "details": {
                            "Result": "SKIP"
                        }
                }
            )
            
            self.datadog_logging(
                "info" if self.result_flashing_fw_h2_label.cget("text") == "Completed" else "error",
                {
                        "summary": "End: Flashing ESP32H2 firmware",
                        "item": "Flashing ESP32H2 firmware",
                        "details": {
                            "Result": "SKIP"
                        }
                }
            )

        if retest_flag == 0:
            self.status_flashing_cert.config(fg="blue")
            self.status_flashing_cert.grid()

            secureCertPartition_data_array = secureCertPartition_data.split('_')
            device_uuid = secureCertPartition_data_array[0]
            print(device_uuid)

            logger.info("Flashing esp32s3 certificate")
            self.datadog_logging(
                "info",
                {
                        "summary": "Flashing esp32s3 certificate"
                }
            )
            print("Flashing esp32s3 certificate")
            
            start_time_dac = datetime.now()
            print("Start Time DAC: ", start_time_dac)

            if check_esp32s3_module == 1:
                logger.info(f"Flashing esp32s3 certificate, Port: {esp32s3_module_port}, Baud: {esp32s3_module_baud}")

                logger.info(f"ESP32S3 Secure Cert Partition Address: {esp32s3_securecert_partition}")
                logger.info(f"ESP32S3 Data Provider Partition Address: {esp32s3_data_provider_partition}")
                logger.info(f"ESP32S3 DAC Use ESPTOOL: {esp32s3_dac_use_esptool}")
                logger.info(f"ESP32S3 DAC Production Mode: {esp32s3_dac_production_mode}")
                logger.info(f"ESP32S3 DAC Folder Name: {esp32s3_dac_folder_name}")
                
                self.datadog_logging(
                    "info",
                    {
                            "summary": f"Start: Flashing DAC",
                            "item": "Flashing DAC",
                            "details": {
                                "Action": "Flashing ESP32S3 certificate",
                                "Port": esp32s3_module_port,
                                "Baud": esp32s3_module_baud,
                                "Secure Cert Partition Address": esp32s3_securecert_partition,
                                "Data Provider Partition Address": esp32s3_data_provider_partition,
                                "ESPTool": esp32s3_dac_use_esptool,
                                "Mode": esp32s3_dac_production_mode,
                                "DAC": esp32s3_dac_folder_name
                            }
                    }
                )
                

                print(f"Flashing esp32s3 certificate, Port: {esp32s3_module_port}, Baud: {esp32s3_module_baud}")
                
                print(f"ESP32S3 Secure Cert Partition Address: {esp32s3_securecert_partition}")
                print(f"ESP32S3 Data Provider Partition Address: {esp32s3_data_provider_partition}")
                print(f"ESP32S3 Use ESPTOOL: {esp32s3_data_provider_partition}")
                print(f"ESP32S3 DAC Use ESPTOOL: {esp32s3_dac_use_esptool}")
                print(f"ESP32S3 DAC Production Mode: {esp32s3_dac_production_mode}")
                print(f"ESP32S3 DAC Folder Name: {esp32s3_dac_folder_name}")

                # self.flashFw.get_esptool_device_mac_address(selected_port, selected_baud)
                self.flashCertificate(esp32s3_dac_use_esptool, 
                                    esp32s3_dac_production_mode,
                                    esp32s3_module_port, 
                                    esp32s3_module_baud, 
                                    serialID_label, 
                                    serialID_data, 
                                    esp32s3_dac_folder_name, 
                                    secureCertPartition_label, 
                                    device_uuid, 
                                    macAddress_label, 
                                    macAddress_esp32s3_data, 
                                    esp32s3_securecert_partition, 
                                    esp32s3_data_provider_partition
                                    )
                # self.flashCertificate(esp32s3_port, serialID_data, self.selected_cert_id)
                # self.flashCertificate("/dev/ttyUSB0", self.selected_cert_id)
            else:
                logger.info(f"Flashing esp32s3 certificate, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
                
                logger.info(f"ESP32S3 Secure Cert Partition Address: {esp32s3_securecert_partition}")
                logger.info(f"ESP32S3 Data Provider Partition Address: {esp32s3_data_provider_partition}")
                logger.info(f"ESP32S3 DAC Use ESPTOOL: {esp32s3_dac_use_esptool}")
                logger.info(f"ESP32S3 DAC Production Mode: {esp32s3_dac_production_mode}")
                logger.info(f"ESP32S3 DAC Folder Name: {esp32s3_dac_folder_name}")
                
                self.datadog_logging(
                    "info",
                    {
                            "summary": f"Start: Flashing DAC",
                            "item": "Flashing DAC",
                            "details": {
                                "Action": "Flashing ESP32S3 certificate",
                                "Port": esp32s3_module_port,
                                "Baud": esp32s3_module_baud,
                                "Secure Cert Partition Address": esp32s3_securecert_partition,
                                "Data Provider Partition Address": esp32s3_data_provider_partition,
                                "ESPTool": esp32s3_dac_use_esptool,
                                "Mode": esp32s3_dac_production_mode,
                                "DAC": esp32s3_dac_folder_name
                            }
                    }
                )
                

                print(f"Flashing esp32s3 certificate, Port: {esp32s3_port}, Baud: {esp32s3_baud}")

                print(f"ESP32S3 Secure Cert Partition Address: {esp32s3_securecert_partition}")
                print(f"ESP32S3 Data Provider Partition Address: {esp32s3_data_provider_partition}")
                print(f"ESP32S3 Use ESPTOOL: {esp32s3_data_provider_partition}")
                print(f"ESP32S3 DAC Use ESPTOOL: {esp32s3_dac_use_esptool}")
                print(f"ESP32S3 DAC Production Mode: {esp32s3_dac_production_mode}")
                print(f"ESP32S3 DAC Folder Name: {esp32s3_dac_folder_name}")

                # self.flashFw.get_esptool_device_mac_address(selected_port, selected_baud)
                self.flashCertificate(esp32s3_dac_use_esptool, 
                                    esp32s3_dac_production_mode,
                                    esp32s3_port, 
                                    esp32s3_baud, 
                                    serialID_label, 
                                    serialID_data, 
                                    esp32s3_dac_folder_name, 
                                    secureCertPartition_label, 
                                    device_uuid, 
                                    macAddress_label, 
                                    macAddress_esp32s3_data, 
                                    esp32s3_securecert_partition, 
                                    esp32s3_data_provider_partition
                                    )
                # self.flashCertificate(esp32s3_port, serialID_data, self.selected_cert_id)
                # self.flashCertificate("/dev/ttyUSB0", self.selected_cert_id)

            # time.sleep(10)
            # time.sleep(20)
            # time.sleep(1)

            if self.result_flashing_cert_label.cget("text") == "Not Yet":
                self.result_flashing_cert_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                self.handle_exit_correctly()
                self.datadog_logging(
                    "error",
                    {
                            "summary": "Failed to flash ESP32S3 DAC"
                        }
                )
                logger.info("Failed to flash ESP32S3 DAC")
                print("Failed to flash ESP32S3 DAC")
                messagebox.showerror("Error", "Fail to flash ESP32S3 DAC, Please make sure the port is correct.")
                return True
            
            else:
                pass
            
            end_time_dac = datetime.now()
            print("End Time DAC: ", end_time_dac)
            
            duration_dac = end_time_dac - start_time_dac
            
            self.datadog_logging(
                "info" if self.result_flashing_cert_label.cget("text") == "Completed" else "error",
                {
                        "summary": "End: Flashing ESP32S3 certificate",
                        "item": "Flashing DAC",
                        "start_time": str(start_time_dac),
                        "end_time": str(end_time_dac),
                        "duration": str(duration_dac),
                        "details": {
                            "Result": "Completed" if self.result_flashing_cert_label.cget("text") == "Completed" else "Failed"
                        }
                }
            )
                        

            self.status_flashing_cert.config(fg="black")
            self.status_flashing_cert.grid()
        else:
            logger.info("Skip Flashing esp32s3 certificate")
            print("Skip Flashing esp32s3 certificate")

            self.result_flashing_cert_label.config(text="SKIP", fg="black", font=("Helvetica", 10, "bold"))
            self.result_flashing_cert_label.grid()

            self.datadog_logging(
                "info" if self.result_flashing_cert_label.cget("text") == "Completed" else "error",
                {
                        "summary": "End: Flashing ESP32S3 certificate",
                        "item": "Flashing DAC",
                        "details": {
                            "Result": "SKIP"
                        }
                }
            )

        # # export the ESP-IDF path
        # self.flashFw.export_esp_idf_path()

        # self.datadog_logging("info","Test 1 Completed")
        self.datadog_logging(
            "info",
            {
                    "summary": "Test 1 Completed"
            }
        )
        logger.info("Test 1 Completed")
        print("Test 1 Completed")

        # Signal that task 1 is complete
        self.task1_completed.set()

        return False

    def start_task1_thread(self):
        self.task1_thread = threading.Thread(target=self.start_test)
        self.task1_thread.start()
        print("start_task1_thread")
        return self.task1_thread
        # return self.start_test()

    def start_check_module(self):
        global check_esp32s3_module

        print("Start Check ESP32S3 Module")
        check_esp32s3_module = 1
        self.combine_tasks()

    def extract_ip_from_dnsmasq_leases(self, filename, device_name):
        with open(filename, 'r') as file:
            for line in file:
                # Check if the device name is in the line
                logger.info(line)
                self.datadog_logging("info", line)
                print(line)
                if device_name in line:
                    # Use regex to extract the IP address
                    match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', line)
                    if match:
                        return match.group(0)  # Return the matched IP address
        return None  # Return None if no match found

    # Function: simple_httpc2device_current_state
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def simple_httpc2device_current_state(self, ip_address):
        # Create a connection object
        conn = http.client.HTTPConnection(f"{ip_address}")
        print(f"Connecting to {ip_address}")

        # Send a GET request
        conn.request("GET", "/current_state")

        # Get the response
        response = conn.getresponse()

        # Read and print the response data
        data = response.read().decode("utf-8")
        logger.info(response.status)
        # self.datadog_logging("info", response.status)
        self.datadog_logging(
            "info",
            {
                    "summary": response.status
            }
        )
        print("Status:", response.status)

        logger.info(data)
        # self.datadog_logging("info", data)
        self.datadog_logging(
            "info",
            {
                    "summary": data
            }
        )
        print("Response:", data)

        # Close the connection
        conn.close()

        return data
    
    # Function: terminate_task_thread
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def terminate_task_thread(self):
    #     # Wait for task 1 to complete
    #     self.handle_exit_correctly()
    #     print(f"A: self.task1_thread: {self.task1_thread} & self.task1_thread_failed: {self.task1_thread_failed}")
    #     print(f"A: self.task2_thread: {self.task2_thread} & self.task2_thread_failed: {self.task2_thread_failed}")
    #     if self.task1_thread_failed.is_set():
    #         print(f"B: self.task1_thread: {self.task1_thread} & self.task1_thread_failed: {self.task1_thread_failed}")
    #         self.task1_thread.join()
    #         if self.task1_thread.is_alive():
    #             print("Task 1 is still running")
    #             messagebox.showerror("Error", "Task 1 is still running")
    #             self.task1_thread_failed.set()
    #             self.task1_thread.join()
    #         self.task1_thread = None
            
    #     elif self.task2_thread_failed.is_set():
    #         print(f"B: self.task2_thread: {self.task2_thread} & self.task2_thread_failed: {self.task2_thread_failed}")
    #         self.task2_thread_failed.set()
    #         self.task2_thread.join()
    #         self.task2_thread = None
    #     else:
    #         pass
        
        while not self.task1_completed.is_set():
            if self.task1_thread_failed.is_set():
                # self.datadog_logging("error","System Error occured on Test 1, unable to proceed.")
                self.datadog_logging(
                    "error",
                    {
                            "summary": "System Error occured on Test 1, unable to proceed."
                    }
                )
                logger.error("System Error occured on Test 1, unable to proceed.")
                logger.info("System Error occured on Test 1, unable to proceed.")
                print("System Error occured on Test 1, unable to proceed.")
                # self.handle_exit_correctly()
                time.sleep(2)
                # messagebox.showerror("Error", "Test Stop! Please check ports configuration")
                return True
            
            if self.task2_thread_failed.is_set():
                # self.datadog_logging("error","System Error occured on Test 2, unable to proceed.")
                self.datadog_logging(
                    "error",
                    {
                            "summary": "System Error occured on Test 2, unable to proceed."
                    }
                )
                logger.info("System Error occured on Test 2, unable to proceed.")
                print("System Error occured on Test 2, unable to proceed.")
                # self.handle_exit_correctly()
                time.sleep(2)
                # messagebox.showerror("Error", "Test Stop! Please check ports configuration")
                return True
            else:
                logger.info(f"Waiting for Test 1 to complete")
                # print(f"Waiting for Test 1 to complete")
                time.sleep(1)
                return False

    # Function: start_test2
    # Modified by: Anuar
    # Last Modified: 22/11/2024
    # Reason for Modification: Added datadog_logging for consistent logging.
    def start_test2(self):
        global factory_app_version
        global device_data
        global orderNum_label
        global macAddress_label
        global serialID_label
        global certID_label
        global secureCertPartition_label
        global commissionableDataPartition_label
        global qrCode_label
        global manualCode_label
        global discriminator_label
        global passcode_label
        global orderNum_data
        global macAddress_esp32s3_data
        global serialID_data
        global certID_data
        global secureCertPartition_data
        global commissionableDataPartition_data
        global qrCode_data
        global manualCode_data
        global discriminator_data
        global passcode_data

        global ini_file_name
        global script_dir

        global break_printer

        global yes_no_button_handling_sequence

        global disable_sticker_printing

        global firmware_version_string

        global orderNumber
        
        global flash_only_flag

        # Check in the specified directory
        ini_file_path = os.path.join(script_dir, ini_file_name)

        if not os.path.exists(ini_file_path):
            logger.error(f"{ini_file_name} not found in the specified directory: {script_dir}")
            self.datadog_logging(
                "error",
                {
                        "summary": f"{ini_file_name} not found in the specified directory: {script_dir}"
                }
            )
            print(f"{ini_file_name} not found in the specified directory: {script_dir}")
            return

        # Proceed to load and process the INI file
        self.loadTestScript = LoadTestScript(ini_file_path)

        config = configparser.ConfigParser()
        config.read(ini_file_path)

        # Wait for task 1 to complete
        while not self.task1_completed.is_set():
            if self.task1_thread_failed.is_set():
                logger.info("System Error occured on Test 1, unable to proceed.")
                # self.datadog_logging("error","System Error occured on Test 1, unable to proceed.")
                self.datadog_logging(
                    "error",
                    {
                            "summary": "System Error occured on Test 1, unable to proceed."
                    }
                )
                print("System Error occured on Test 1, unable to proceed.")
                self.handle_exit_correctly()
                time.sleep(2)
                messagebox.showerror("Error", "System Error occured on Test 1, unable to proceed.")
                return True
            
            if self.task2_thread_failed.is_set():
                logger.info("System Error occured on Test 2, unable to proceed.")
                # self.datadog_logging("error","System Error occured on Test 2, unable to proceed.")
                self.datadog_logging(
                    "error",
                    {
                            "summary": "System Error occured on Test 2, unable to proceed."
                    }
                )
                print("System Error occured on Test 2, unable to proceed.")
                self.handle_exit_correctly()
                time.sleep(2)
                messagebox.showerror("Error", "System Error occured on Test 2, unable to proceed.")
                return True
            
            if self.stop_event.is_set():
                logger.info("System Force Stop")
                # self.datadog_logging("error","System Force Stop")
                self.datadog_logging(
                    "error",
                    {
                            "summary": "System Force Stop"
                    }
                )
                print("System Force Stop")
                self.handle_exit_correctly()
                time.sleep(2)
                messagebox.showerror("Error", "System Force Stop")
                return True

            else:
                logger.info(f"Waiting for Test 1 to complete")
                # print(f"Waiting for Test 1 to complete")
                pass

            time.sleep(1)

        # self.terminate_task_thread()

        if check_esp32s3_module == 1:
            logger.info("Start Check ESP32S3 Module")
            print("Start Check ESP32S3 Module")
            
            # self.datadog_logging("info","Start Check ESP32S3 Module")
            self.datadog_logging(
                "info",
                {
                        "summary": "Start Check ESP32S3 Module"
                }
            )


        else:
            if flash_only_flag == 0:
                self.terminate_task_thread()
                logger.info("Test 2 Start")
                print("Test 2 Start")
                
                # self.datadog_logging("info","Test 2 Start")
                self.datadog_logging(
                    "info",
                    {
                            "summary": "Test 2 Start"
                    }
                )

                self.status_factory_mode.config(fg="blue")
                self.status_factory_mode.grid()

                if "factory_esp32s3" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""      
                    
                    test_start_time = datetime.now()    

                    logger.info(f"Start Time: {test_start_time}")
                    
                    
                    logger.info("Entering factory mode")
                    print("Entering factory mode")
                    
                    # self.datadog_logging("info","Entering factory mode")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Entering factory mode"
                        }
                    )

                    # try:
                    esp32s3_port = self.port_var.get()
                    # esp32s3_port = "/dev/ttyACM0"
                    esp32s3_baud = int(self.baud_var.get())

                    esp32s3_factory_port = self.port_var1.get()
                    esp32s3_factory_baud = int(self.baud_var1.get())

                    esp32h2_port = self.port_var2.get()
                    esp32h2_baud = int(self.baud_var2.get())

                    if self.stop_event.is_set():
                        logger.info("System Force Stop")
                        # self.datadog_logging("error","System Force Stop")
                        self.datadog_logging(
                            "error",
                            {
                                    "summary": "System Force Stop"
                            }
                        )
                        print("System Force Stop")
                        self.handle_exit_correctly()
                        time.sleep(2)
                        messagebox.showerror("Error", "System Force Stop")
                        return True

                    logger.info("Open esp32s3 Factory Port")
                    print("Open esp32s3 Factory Port")
                    logger.info(f"factory Port: {esp32s3_factory_port}, Baud: {esp32s3_factory_baud}")
                    # self.datadog_logging("info",f"Open esp32s3 Factory Port. Port: {esp32s3_factory_port}, Baud: {esp32s3_factory_baud}")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Open ESP32S3 Factory Port"
                        }
                    )
                    if self.serialCom.open_serial_port(esp32s3_factory_port, esp32s3_factory_baud):
                        self.handle_exit_correctly()
                        logger.info("Failed to open esp32s3 factory port")
                        self.datadog_logging(
                            "error",
                            {
                                    "summary": "Failed to open esp32s3 factory port"
                                }
                        )
                        print("Failed to open esp32s3 factory port")
                        messagebox.showerror("Error", "Failed to open esp32s3 factory port")
                        return True

                    logger.info("Reboot esp32s3 and esp32h2")
                    print("Reboot esp32s3 and esp32h2")
                    logger.info(f"Reboot esp32s3, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
                    logger.info(f"Reboot esp32h2, Port: {esp32h2_port}, Baud: {esp32h2_baud}")
                    self.reboot_h2(True, esp32h2_port, esp32h2_baud)
                    self.reboot_s3(False, True, esp32s3_port, esp32s3_baud)
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "End: Entering factory mode",
                                "item": "Factory mode",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Reboot ESP32S3": f"Port: {esp32s3_port}, Baud: {esp32s3_baud}",
                                    "Reboot ESP32H2": f"Port: {esp32h2_port} Baud: {esp32h2_baud}"
                                }
                        }
                    )

                    
                    logger.info("Start Wait 3")
                    print("Start Wait 3")
                    time.sleep(3)
                    logger.info("Finish Wait 3")
                    
                    print("Finish Wait 3")

                    # except configparser.NoOptionError:
                    #     logger.error("Port not found in the INI file")
                    #     print("Port not found in the INI file")

                self.status_factory_mode.config(fg="black")
                self.status_factory_mode.grid()

                # time.sleep(1)

                self.status_read_device_mac.config(fg="blue")
                self.status_read_device_mac.grid()

                if "read_mac_address" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    logger.info("Read MAC Address")
                    # self.datadog_logging("info","Start: Read MAC Address")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device MAC Address",
                                "item": "Read Device MAC"
                        }
                    )
                    print("Read MAC Address")
                    # self.get_device_mac()
                    command = config.get("read_mac_address", "read_mac_address_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read MAC Address Command: {command}")
                    print(f"Read MAC Address Command: {command}")
                    logger.info(f"Reference MAC Address: {macAddress_esp32s3_data}")
                    print(f"Reference MAC Address: {macAddress_esp32s3_data}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond

                    # This is to update ui if the device successfully enter into factory mode
                    if self.result_factory_mode_label.cget("text") == "Not Yet":
                        self.result_factory_mode_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        test_result = "Failed"
                    else:
                        pass

                    if self.read_device_mac.cget("text") == str(macAddress_esp32s3_data):
                        self.result_read_device_mac.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Read MAC Address: Pass")
                        print("Read MAC Address: Pass")
                        test_result = "Pass"
                        
                        # self.handle_exit_correctly()
                        # messagebox.showerror("Error", "Test Stop!")
                        # return True
                    else:
                        self.result_read_device_mac.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Read MAC Address: Failed")
                        print("Read MAC Address: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1

                        self.handle_exit_correctly()
                        messagebox.showerror("Error", "ESP32S3 MAC Address missmatch!")
                        return True

                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read MAC Address,\n"
                    #     f"Read Mac Address Command: {command},\n"
                    #     f"Reference MAC Address: {macAddress_esp32s3_data},\n"
                    #     f"Device MAC Address: {self.read_device_mac.cget('text')},\n"
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    print(f"Duration: End Time {end_time} - Start Time {test_start_time}: ", duration)

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Device MAC",
                                "item": "Read Device MAC",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read Device MAC",
                                    "Command": command,
                                    "Reference": macAddress_esp32s3_data,
                                    "Actual": self.read_device_mac.cget('text'),
                                    "Result": test_result
                                }
                        }
                    )

                self.status_read_device_mac.config(fg="black")
                self.status_read_device_mac.grid()

                self.status_read_device_firmware_version.config(fg="blue")
                self.status_read_device_firmware_version.grid()

                if "read_firmware_version" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    
                    logger.info("Read Firmware Version")
                    # self.datadog_logging("info","Start: Read Firmware Version")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device Firmware",
                                "item": "Read Device Firmware"
                                }
                    )
                    print("Read Firmware Version")
                    # self.get_device_mac()
                    command = config.get("read_firmware_version", "read_firmware_version_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Firmware Command: {command}")
                    print(f"Read Firmware Command: {command}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    correct_firmware_version = config.get("read_firmware_version", "correct_firmware_version")
                    logger.info(f"Correct Firmware Version: {correct_firmware_version}")
                    print(f"Correct Firmware Version: {correct_firmware_version}")
                    firmware_version_string = self.read_device_firmware_version.cget("text")
                    logger.info(f"Read Firwmare Version: {firmware_version_string}")
                    print(f"Read Firwmare Version: {firmware_version_string}")
                    if self.read_device_firmware_version.cget("text") == str(correct_firmware_version):
                        self.result_read_device_firmware_version.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Read Firwmare Version: Pass")
                        print("Read Firwmare Version: Pass")
                        test_result = "Pass"
                        
                        # self.handle_exit_correctly()
                        # messagebox.showerror("Error", "Test Stop!")
                        # return True
                    else:
                        self.result_read_device_firmware_version.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Read Firwmare Version: Failed")
                        print("Read Firwmare Version: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1

                        self.handle_exit_correctly()
                        messagebox.showerror("Error", "Wrong Firmware Version!")
                        return True
                    
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Firmware Version,\n"
                    #     f"Read Firmware Command: {command},\n"
                    #     f"Reference Firmwre Version: {correct_firmware_version},\n"
                    #     f"Device Firmware Version: {firmware_version_string},\n"
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    print(f"Duration: End Time {end_time} - Start Time {test_start_time}: ", duration)

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Device Firmware",
                                "item": "Read Device Firmware",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read Device Firmware",
                                    "Command": command,
                                    "Reference": correct_firmware_version,
                                    "Actual": firmware_version_string,
                                    "Result": test_result
                                }
                        }
                    )

                self.status_read_device_firmware_version.config(fg="black")
                self.status_read_device_firmware_version.grid()

                self.status_read_prod_name.config(fg="blue")
                self.status_read_prod_name.grid()

                if "write_product_name" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    logger.info("Write Product Name")
                    # self.datadog_logging("info","Start: Write Product Name")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Product Name",
                                "item": "Product Name"
                            }
                    )
                    print("Write Product Name")
                    command = config.get("write_product_name", "write_product_name_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Write Product Name Command: {command}")
                    print(f"Write Product Name Command: {command}")
                    time.sleep(self.step_delay)
                    # self.datadog_logging("info","End: Write Product Name")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "End: Product Name",
                                "item": "Product Name"
                        }
                    )

                if "read_product_name" in config:
                    logger.info("Read Product Name")
                    # self.datadog_logging("info","Start: Read Product Name")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Product Name",
                                "item": "Product Name"
                        }
                    )
                    print("Read Product Name")
                    command = config.get("read_product_name", "read_product_name_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Product Name Command: {command}")
                    print(f"Read Product Name Command: {command}")
                    data = config.get("read_product_name", "read_product_name_data")
                    logger.info(f"Reference Product Name: {data}")
                    print(f"Reference Product Name: {data}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    if self.read_prod_name.cget("text") == str(data):
                        self.result_read_prod_name.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Product Name: Pass")
                        print("Product Name: Pass")
                        test_result = "Pass"
                    else:
                        self.result_read_prod_name.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Product Name: Failed")
                        print("Product Name: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Product Name,\n"
                    #     f"Read Product Name Command: {command},\n"
                    #     f"Reference Product Name: {data},\n"
                    #     f"Device Product Name: {self.read_prod_name.cget('text')},\n" 
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    print(f"Duration: End Time {end_time} - Start Time {test_start_time}: ", duration)
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Product Name",
                                "item": "Product Name",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Product Name",
                                    "Command": command,
                                    "Reference": data,
                                    "Actual": self.read_prod_name.cget('text'),
                                    "Result": test_result
                                }
                        }
                    )

                self.status_read_prod_name.config(fg="black")
                self.status_read_prod_name.grid()

                self.status_write_device_sn.config(fg="blue")
                self.status_write_device_sn.grid()

                if "write_serial_number" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""

                    logger.info("Write Device S/N")
                    # self.datadog_logging("info","Start: Write Device S/N")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Write Device S/N",
                                "item": "Write Device S/N"
                        }
                    )
                    print("Write Device S/N")
                    # self.send_serial_number(serialID_data)
                    command = config.get("write_serial_number", "write_serial_number_command")
                    command = command + str(serialID_data)
                    self.send_command(command + "\r\n")
                    logger.info(f"Write Device S/N Command: {command}")
                    print(f"Write Device S/N Command: {command}")
                    time.sleep(self.step_delay)
                    # self.datadog_logging("info","End: Write Device S/N")

                if "read_serial_number" in config:
                    logger.info("Read Serial Number")
                    # self.datadog_logging("info","Start: Read Serial Number")

                    print("Read Serial Number")
                    # self.send_serial_number(serialID_data)
                    command = config.get("read_serial_number", "read_serial_number_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Serial Number Command: {command}")
                    print(f"Read Serial Number Command: {command}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    if self.read_device_sn.cget("text") == str(serialID_data):
                        self.result_write_serialnumber.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Write Device S/N: Pass")
                        print("Write Device S/N: Pass")
                        test_result = "Pass"
                    else:
                        self.result_write_serialnumber.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Write Device S/N: Failed")
                        print("Write Device S/N: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Serial Number,\n"
                    #     f"Read Serial Number Command: {command},\n"
                    #     f"Reference Serial Number: {serialID_data},\n"
                    #     f"Device Serial Number: {self.read_device_sn.cget('text')},\n" 
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Serial Number",
                                "item": "Write Device S/N",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {                       
                                    "Action": "Read Serial Number",
                                    "Command": command,
                                    "Reference": serialID_data,
                                    "Actual": self.read_device_sn.cget('text'),
                                    "Result": test_result
                                }
                        }
                    )


                self.status_write_device_sn.config(fg="black")
                self.status_write_device_sn.grid()
            
                self.status_read_device_matter_dac_vid.config(fg="blue")
                self.status_read_device_matter_dac_vid.grid()

                if "read_dac_vid" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                                    
                    logger.info("Read Device Matter DAC VID")
                    # self.datadog_logging("info","Start: Read Device Matter DAC VID")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device Matter DAC VID",
                                "item": "Read Device Matter DAC VID"
                        }
                    )
                    print("Read Device Matter DAC VID")
                    # self.send_mqtr(qrCode_data)
                    command = config.get("read_dac_vid", "read_dac_vid_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Device Matter DAC VID Command: {command}")
                    print(f"Read Device Matter DAC VID Command: {command}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    if f"{orderNumber}" == "hand-sample" or f"{orderNumber}" == "200-trial-run":
                        correct_dac_vid = config.get("read_vid", "correct_vid")
                    else:
                        correct_dac_vid = config.get("read_dac_vid", "correct_dac_vid")
                    logger.info(f"Correct Matter DAC VID: {correct_dac_vid}")
                    print(f"Correct Matter DAC VID: {correct_dac_vid}")
                    if f"{firmware_version_string}" == correct_firmware_version:
                        if self.read_device_matter_dac_vid.cget("text") == str(correct_dac_vid):
                            self.result_read_device_matter_dac_vid.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("Read Device Matter DAC VID: Pass")
                            print("Read Device Matter DAC VID: Pass")
                            test_result = "Pass"
                        else:
                            self.result_read_device_matter_dac_vid.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("Read Device Matter DAC VID: Failed")
                            print("Read Device Matter DAC VID: Failed")
                            test_result = "Failed"

                            disable_sticker_printing = 1
                    else:
                        self.result_read_device_matter_dac_vid.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Read Device Matter DAC VID: Pass")
                        print("Read Device Matter DAC VID: Pass")
                        test_result = "Pass"
                    
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Device Matter DAC VID,\n"
                    #     f"Read Device Matter DAC VID Command: {command},\n"
                    #     f"Correct Matter DAC VID: {correct_dac_vid},\n"
                    #     f"Device Matter DAC VID: {self.read_device_matter_dac_vid.cget('text')},\n" 
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
            
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Device Matter DAC VID",
                                "item": "Read Device Matter DAC VID",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read Device Matter DAC VID",
                                    "Command": command,
                                    "Reference": correct_dac_vid,
                                    "Actual": self.read_device_matter_dac_vid.cget('text'),
                                    "Result": test_result
                                }
                        }
                    )

                self.status_read_device_matter_dac_vid.config(fg="black")
                self.status_read_device_matter_dac_vid.grid()

                self.status_read_device_matter_dac_pid.config(fg="blue")
                self.status_read_device_matter_dac_pid.grid()

                if "read_dac_pid" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""                
                    
                    logger.info("Read Device Matter DAC PID")
                    # self.datadog_logging("info","Start: Read Device Matter DAC PID")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device Matter DAC PID",
                                "item": "Read Device Matter DAC PID"
                        }
                    )
                    print("Read Device Matter DAC PID")
                    # self.send_mqtr(qrCode_data)
                    command = config.get("read_dac_pid", "read_dac_pid_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Device Matter DAC PID Command: {command}")
                    print(f"Read Device Matter DAC PID Command: {command}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    if f"{orderNumber}" == "hand-sample" or f"{orderNumber}" == "200-trial-run":
                        correct_dac_pid = config.get("read_pid", "correct_pid")
                    else:
                        correct_dac_pid = config.get("read_dac_pid", "correct_dac_pid")
                    logger.info(f"Correct Matter DAC PID: {correct_dac_pid}")
                    print(f"Correct Matter DAC PID: {correct_dac_pid}")
                    if f"{firmware_version_string}" == correct_firmware_version:
                        if self.read_device_matter_dac_pid.cget("text") == str(correct_dac_pid):
                            self.result_read_device_matter_dac_pid.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("Read Device Matter DAC VID: Pass")
                            print("Read Device Matter DAC VID: Pass")
                            test_result = "Pass"
                        else:
                            self.result_read_device_matter_dac_pid.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("Read Device Matter DAC VID: Failed")
                            print("Read Device Matter DAC VID: Failed")
                            test_result = "Failed"
                        
                            disable_sticker_printing = 1
                    else:
                        self.result_read_device_matter_dac_pid.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Read Device Matter DAC VID: Pass")
                        print("Read Device Matter DAC VID: Pass")
                        test_result = "Pass"
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Device Matter DAC PID,\n"
                    #     f"Read Device Matter DAC PID Command: {command},\n"
                    #     f"Correct Matter DAC PID: {correct_dac_pid},\n" 
                    #     f"Device Matter DAC PID: {self.read_device_matter_dac_pid.cget('text')},\n" 
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Device Matter DAC PID",
                                "item": "Read Device Matter DAC PID",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read Device Matter DAC PID",
                                    "Command": command,
                                    "Reference": correct_dac_pid,
                                    "Actual": self.read_device_matter_dac_pid.cget('text'),
                                    "Result": test_result
                            }
                        }
                    )

                self.status_read_device_matter_dac_pid.config(fg="black")
                self.status_read_device_matter_dac_pid.grid()

                self.status_read_device_matter_vid.config(fg="blue")
                self.status_read_device_matter_vid.grid()

                if "read_vid" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    logger.info("Read Device Matter VID")
                    # self.datadog_logging("info","Start: Read Device Matter VID")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device Matter VID",
                                "item": "Read Device Matter VID"
                        }
                    )
                    print("Read Device Matter VID")
                    # self.send_mqtr(qrCode_data)
                    command = config.get("read_vid", "read_vid_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Device Matter VID Command: {command}")
                    print(f"Read Device Matter VID Command: {command}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    if f"{orderNumber}" == "hand-sample" or f"{orderNumber}" == "200-trial-run":
                        # correct_vid = str("0")
                        correct_vid = config.get("read_vid", "correct_vid")
                    else:
                        correct_vid = config.get("read_vid", "correct_vid")
                    logger.info(f"Correct Matter VID: {correct_vid}")
                    print(f"Correct Matter VID: {correct_vid}")
                    if self.read_device_matter_vid.cget("text") == str(correct_vid):
                        self.result_read_device_matter_vid.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Read Device Matter VID: Pass")
                        print("Read Device Matter VID: Pass")
                        test_result = "Pass"
                    elif self.read_device_matter_vid.cget("text") == str("0"):
                        self.result_read_device_matter_vid.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Read Device Matter VID: Pass")
                        print("Read Device Matter VID: Pass")
                        test_result = "Pass"

                        logger.info(f"Device firmware version: {firmware_version_string}")
                        print(f"Device firmware version: {firmware_version_string}")
                        logger.info(f"Firmware version older than 1.0.0-rc10 do not support read out Matter VID!")
                        print(f"Firmware version older than 1.0.0-rc10 do not support read out Matter VID!")
                    else:
                        self.result_read_device_matter_vid.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Read Device Matter VID: Failed")
                        print("Read Device Matter VID: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Device Matter VID,\n"
                    #     f"Read Device Matter VID Command: {command},\n"
                    #     f"Reference Matter VID: {correct_vid},\n"
                    #     f"Device Matter VID: {self.read_device_matter_vid.cget('text')},\n"
                    #     f"Result: {test_result},\n"
                    #     f"Firmware version: {firmware_version_string},\n"
                    #     f"Message: Device firmware version older than 1.0.0-rc10 do not support read out Matter VID!"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Device Matter VID",
                                "item": "Read Device Matter VID",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read Device Matter VID",
                                    "Command": command,
                                    "Reference": correct_vid,
                                    "Actual": self.read_device_matter_vid.cget('text'),
                                    "Result": test_result,
                            }
                        }
                    )

                self.status_read_device_matter_vid.config(fg="black")
                self.status_read_device_matter_vid.grid()

                self.status_read_device_matter_pid.config(fg="blue")
                self.status_read_device_matter_pid.grid()

                if "read_pid" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                                
                    logger.info("Read Device Matter PID")
                    # self.datadog_logging("info","Start: Read Device Matter PID")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device Matter PID",
                                "item": "Read Device Matter PID"
                        }
                    )
                    print("Read Device Matter PID")
                    # self.send_mqtr(qrCode_data)
                    command = config.get("read_pid", "read_pid_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Device Matter PID Command: {command}")
                    print(f"Read Device Matter PID Command: {command}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    if f"{orderNumber}" == "hand-sample" or f"{orderNumber}" == "200-trial-run":
                        # correct_pid = str("0")
                        correct_pid = config.get("read_pid", "correct_pid")
                    else:
                        correct_pid = config.get("read_pid", "correct_pid")
                    logger.info(f"Correct Matter PID: {correct_pid}")
                    print(f"Correct Matter PID: {correct_pid}")
                    if f"{firmware_version_string}" == correct_firmware_version:
                        if self.read_device_matter_pid.cget("text") == str(correct_pid):
                            self.result_read_device_matter_pid.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("Read Device Matter VID: Pass")
                            print("Read Device Matter VID: Pass")
                            test_result = "Pass"
                        elif self.read_device_matter_pid.cget("text") == str("0"):
                            self.result_read_device_matter_pid.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("Read Device Matter VID: Pass")
                            print("Read Device Matter VID: Pass")
                            test_result = "Pass"

                            logger.info(f"Device firmware version: {firmware_version_string}")
                            print(f"Device firmware version: {firmware_version_string}")
                            logger.info(f"Firmware version older than 1.0.0-rc10 do not support read out Matter PID!")
                            print(f"Firmware version older than 1.0.0-rc10 do not support read out Matter PID!")
                        else:
                            self.result_read_device_matter_pid.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("Read Device Matter VID: Failed")
                            print("Read Device Matter VID: Failed")
                            test_result = "Failed"

                            disable_sticker_printing = 1
                            
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Device Matter PID,\n"
                    #     f"Read Device Matter PID Command: {command},\n"
                    #     f"Reference Matter PID: {correct_pid},\n"
                    #     f"Device Matter PID: {self.read_device_matter_pid.cget('text')},\n" 
                    #     f"Result: {test_result},\n"
                    #     f"Firmware version: {firmware_version_string},\n"
                    #     f"Message: Device firmware version older than 1.0.0-rc10 do not support read out Matter PID!"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Device Matter PID",
                                "item": "Read Device Matter PID",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read Device Matter PID",
                                    "Command": command,
                                    "Reference": correct_pid,
                                    "Actual": self.read_device_matter_pid.cget('text'),
                                    "Result": test_result
                            }
                        }
                    )

                self.status_read_device_matter_pid.config(fg="black")
                self.status_read_device_matter_pid.grid()

                self.status_read_device_matter_discriminator.config(fg="blue")
                self.status_read_device_matter_discriminator.grid()

                if "read_matter_discriminator" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    test_start_time = datetime.now()     
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    logger.info("Read Device Matter Discriminator")
                    # self.datadog_logging("info","Start: Read Device Matter Discriminator")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device Matter Discriminator",
                                "item": "Read Device Matter Discriminator"
                        }
                    )
                    print("Read Device Matter Discriminator")
                    # self.send_mqtr(qrCode_data)
                    command = config.get("read_matter_discriminator", "read_matter_discriminator_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Device Matter Discriminator Command: {command}")
                    print(f"Read Device Matter Discriminator Command: {command}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    logger.info(f"Correct Matter Discriminator: {discriminator_data}")
                    print(f"Correct Matter Discriminator: {discriminator_data}")
                    if self.read_device_matter_discriminator.cget("text") == str(discriminator_data):
                        self.result_read_device_matter_discriminator.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Read Device Matter VID: Pass")
                        print("Read Device Matter VID: Pass")
                        test_result = "Pass"
                    else:
                        self.result_read_device_matter_discriminator.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Read Device Matter VID: Failed")
                        print("Read Device Matter VID: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Device Matter Discriminator,\n"
                    #     f"Read Device Matter Discriminator Command: {command},\n"
                    #     f"Reference Matter Discriminator: {discriminator_data},\n"
                    #     f"Device Matter Discriminator: {self.read_device_matter_discriminator.cget('text')},\n" 
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Device Matter Discriminator",
                                "item": "Read Device Matter Discriminator",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read Device Matter Discriminator",
                                    "Command": command,
                                    "Reference": discriminator_data,
                                    "Actual": self.read_device_matter_discriminator.cget('text'),
                                    "Result": test_result #Anuar 27/11 4:02PM
                                }
                        }
                    )

                self.status_read_device_matter_discriminator.config(fg="black")
                self.status_read_device_matter_discriminator.grid()

                self.status_write_device_mtqr.config(fg="blue")
                self.status_write_device_mtqr.grid()

                if "write_matter_qr" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""

                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    logger.info("Write Device Matter QR")
                    # self.datadog_logging("info","Start: Write Device Matter QR")
                                    
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Write Device Matter QR",
                                "item": "Write Device Matter QR"
                        }
                    )
                    print("Write Device Matter QR")
                    # self.send_mqtr(qrCode_data)
                    command = config.get("write_matter_qr", "write_matter_qr_command")
                    command = command + str(qrCode_data)
                    self.send_command(command + "\r\n")
                    logger.info(f"Write Device Matter QR Command: {command}")
                    print(f"Write Device Matter QR Command: {command}")
                    time.sleep(self.step_delay)
                    # self.datadog_logging("info","End: Write Device Matter QR")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "End: Write Device Matter QR",
                                "item": "Write Device Matter QR"
                        }
                    )

                if "read_matter_qr" in config:
                    logger.info("Read Matter QR String")
                    # self.datadog_logging("info","Start: Read Matter QR String")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device Matter QR",
                                "item": "Write Device Matter QR"
                        }
                    )
                    print("Read Matter QR String")
                    # self.send_mqtr(qrCode_data)
                    command = config.get("read_matter_qr", "read_matter_qr_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read Matter QR String Command: {command}")
                    print(f"Read Matter QR String Command: {command}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    if self.read_device_mtqr.cget("text") == str(qrCode_data):
                        self.result_write_mtqr.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Write Device Matter QR: Pass")
                        print("Write Device Matter QR: Pass")
                        test_result = "Pass"
                    else:
                        self.result_write_mtqr.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Write Device Matter QR: Failed")
                        print("Write Device Matter QR: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read Matter QR String,\n"
                    #     f"Read Matter QR String Command: {command},\n"
                    #     f"Reference Matter QR String: {qrCode_data},\n"
                    #     f"Device Matter QR String: {self.read_device_mtqr.cget('text')},\n"
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read Device Matter QR",
                                "item": "Write Device Matter QR",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read Device Matter QR",
                                    "Command": command,
                                    "Reference": qrCode_data,
                                    "Actual": self.read_device_mtqr.cget('text'),
                                    "Result": test_result
                                }
                        }
                    )

                self.status_write_device_mtqr.config(fg="black")
                self.status_write_device_mtqr.grid()

                self.result_ir_def.config(fg="blue")
                self.result_ir_def.grid()

                if "write_ir_definition" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    test_start_time = datetime.now() 
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    logger.info("Write IR Definition")
                    # self.datadog_logging("info","Start: Write IR Definition")
                                    
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Write IR Definition",
                                "item": "Write IR Definition"
                            }
                    )
                    print("Write IR Definition")
                    command = config.get("write_ir_definition", "write_ir_definition_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Write IR Definition Command: {command}")
                    print(f"Write IR Definition Command: {command}")
                    time.sleep(5) # Need to have long wait time due to long command
                    # self.datadog_logging("info","End: Write IR Definition")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "End: Write IR Definition",
                                "item": "Write IR Definition"
                        }
                    )

                if "read_ir_definition" in config:
                    logger.info("Read IR Definition")
                    # self.datadog_logging("info","Start: Read IR Definition")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read IR Definition",
                                "item": "Write IR Definition"
                            }
                    )
                    print("Read IR Definition")
                    command = config.get("read_ir_definition", "read_ir_definition_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read IR Definition Command: {command}")
                    print(f"Read IR Definition Command: {command}")
                    read_ir_def = config.get("read_ir_definition", "read_ir_definition_data")
                    time.sleep(5)  # Need to have long wait time due to long command
                    if self.result_ir_def_label.cget("text") == "Pass":
                        # self.result_ir_def_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("IR Definition Test: Pass")
                        print("IR Definition Test: Pass")
                        test_result = "Pass"
                    else:
                        self.result_ir_def_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("IR Definition: Failed")
                        print("IR Definition Test: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Read IR Definition,\n"
                    #     f"Read IR Definition Command: {command},\n"
                    #     f"Reference IR Definition: {read_ir_def},\n"
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Read IR Definition",
                                "item": "Write IR Definition",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Read IR Definition",
                                    "Command": command,
                                    "Result": test_result
                                }
                            }
                    )

                self.result_ir_def.config(fg="black")
                self.result_ir_def.grid()

                self.status_save_device_data_label.config(fg="blue")
                self.status_save_device_data_label.grid()

                if "save_device_data" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""  
                                    
                    logger.info("Save Device Data")
                    # self.datadog_logging("info","Start: Save Device Data")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Save Device Data",
                                "item": "Save Device Data"
                            }
                    )
                    print("Save Device Data")
                    command = config.get("save_device_data", "save_device_data_command")
                    logger.info(f"Save Device Data Command: {command}")
                    print(f"Save Device Data Command: {command}")
                    data_array = command.split(';')
                    data = data_array[1]
                    logger.info(f"Extracted data: {data}")
                    print(f"Extracted data: {data}")
                    self.send_command(command + "\r\n")

                    start_time = time.time()
                    while time.time() - start_time < float(10):
                        if self.stop_event.is_set():
                                logger.info("System Force Stop")
                                # self.datadog_logging("error","System Force Stop")
                                self.datadog_logging(
                                    "error",
                                    {
                                            "summary": "System Force Stop"
                                        }
                                )
                                print("System Force Stop")
                                self.handle_exit_correctly()
                                time.sleep(2)
                                messagebox.showerror("Error", "System Force Stop")
                                return True
                        time.sleep(1)
                    
                    if self.read_save_device_data_label.cget("text") == str(data.strip()):
                        self.result_save_device_data_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Save Device Data: Pass")
                        print("Save Device Data: Pass")
                        test_result = "Pass"
                    else:
                        self.result_save_device_data_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Save Device Data: Failed")
                        print("Save Device Data: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Save Device Data,\n"
                    #     f"Save Device Data Command: {command},\n"
                    #     f"Extracted data: {data},\n"
                    #     f"Device Data: {self.read_save_device_data_label.cget('text')},\n"
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Save Device Data",
                                "item": "Save Device Data",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Save Device Data",
                                    "Command": command,
                                    "Reference": data,
                                    "Actual": self.read_save_device_data_label.cget('text'),
                                    "Result": test_result
                                    }
                            }
                    )

                self.status_save_device_data_label.config(fg="black")
                self.status_save_device_data_label.grid()
            
                self.status_save_application_data_label.config(fg="blue")
                self.status_save_application_data_label.grid()

                if "save_application_data" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                                                    
                    logger.info("Save Application Data")
                    # self.datadog_logging("info","Start: Save Application Data")
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Save Application Data",
                                "item": "Save Application Data"
                            }
                    )
                    print("Save Application Data")
                    command = config.get("save_application_data", "save_application_data_command")
                    logger.info(f"Save Application Data Command: {command}")
                    print(f"Save Application Data Command: {command}")
                    data_array = command.split(';')
                    data = data_array[1]
                    logger.info(f"Extracted data: {data}")
                    print(f"Extracted data: {data}")
                    self.send_command(command + "\r\n")

                    start_time = time.time()
                    while time.time() - start_time < float(10):
                        if self.stop_event.is_set():
                                logger.info("System Force Stop")
                                # self.datadog_logging("error","System Force Stop")
                                self.datadog_logging(
                                    "error",
                                    {
                                            "summary": "System Force Stop"
                                    }
                                )
                                print("System Force Stop")
                                self.handle_exit_correctly()
                                time.sleep(2)
                                messagebox.showerror("Error", "System Force Stop")
                                return True
                        time.sleep(1)

                    if self.read_save_application_data_label.cget("text") == str(data.strip()):
                        self.result_save_application_data_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Save Application Data: Pass")
                        print("Save Application Data: Pass")
                        test_result = "Pass"
                    else:
                        self.result_save_application_data_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Save Application Data: Failed")
                        print("Save Application Data: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1
                            
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Save Application Data,\n"
                    #     f"Save Application Data Command: {command},\n"
                    #     f"Extracted data: {data},\n"
                    #     f"Device Data: {self.read_save_application_data_label.cget('text')},\n" 
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
            
                    logger.info(f"Duration: {duration}")
                    
                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Save Application Data",
                                "item": "Save Application Data",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Save Application Data",
                                    "Command": command,
                                    "Reference": data,
                                    "Actual": self.read_save_application_data_label.cget('text'),
                                    "Result": test_result
                                }
                        }
                    )

                self.status_save_application_data_label.config(fg="black")
                self.status_save_application_data_label.grid()

                self.status_5v_test.config(fg="blue")
                self.status_5v_test.grid()

                if "5v_test" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = "" 
                    
                    test_start_time = datetime.now()  
                    
                    logger.info(f"Start Time: {test_start_time}")             
                
                    logger.info("5V Test")
                    # self.datadog_logging("info","Start: 5V Test")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: 5V Test",
                                "item": "5V Test"
                        }
                    )
                    print("5V Test")
                    # Test Loop
                    # self.submit_5V_dmm.config(state=tk.NORMAL)
                    auto_mode = config.get("5v_test", "5v_test_auto_mode")
                    logger.info(f"5V Test Auto Mode: {auto_mode}")
                    print(f"5V Test Auto Mode: {auto_mode}")
                    loop_seconds = config.get("5v_test", "5v_test_duration_seconds")
                    logger.info(f"5V Test Time in seconds: {loop_seconds}")
                    print(f"5V Test Time in seconds: {loop_seconds}")
                    test_range = config.get("5v_test", "5v_test_range")
                    logger.info(f"5V Test Range: {test_range} V")
                    print(f"5V Test Range: {test_range}V")
                    
                    upper_limit = 5.0 + float(test_range)
                    lower_limit = 5.0 - float(test_range)
                    
                    self.range_value_5V_dmm.config(text=f"{test_range}", fg="black", font=("Helvetica", 10, "bold"))
                    if auto_mode =="True":
                        self.dmmReader.select_device(0)
                        self.dmm_reader_5V_value_manual(self.input_5V_dmm)
                    label_appear = True
                    start_time = time.time()
                    while time.time() - start_time < float(loop_seconds):
                        if label_appear == True:
                            self.status_5v_test.config(fg="blue")
                            self.status_5v_test.grid()
                            label_appear = False
                        else:
                            self.status_5v_test.config(fg="black")
                            self.status_5v_test.grid()
                            label_appear = True

                        if self.result_5v_test.cget("text") != "Not Yet":
                            break
                        time.sleep(0.5)
                    self.status_5v_test.config(fg="black")
                    self.status_5v_test.grid()
                    device_voltage = self.dmm_5V_reader.cget("text")
                    print(f"Device Voltage: {device_voltage}")

                    if device_voltage == "V":
                        print("5V Test: Failed")
                        test_result = "Failed"
                    else:
                        try:
                            device_voltage = float(self.input_5V_dmm.get())
                        except ValueError:
                            print("5V Test: Failed - Invalid Voltage Value")
                            test_result = "Failed"
                            
                    if self.dmm_5V_reader.cget("text") == "-":
                        self.result_5v_test.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("5V Test: Failed")
                        print("5V Test: Failed")
                        test_result = "Failed"
                        
                    elif self.result_5v_test.cget("text") == "Pass":
                        print("5V Test: Pass")
                        test_result = "Pass"

                        # disable_sticker_printing = 1
                        
                    else:
                        # self.result_5v_test.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("5V Test: Pass")
                        # print("5V Test: Pass")
                        pass
                    
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: 5V Test,\n"
                    #     f"5V Test Auto Mode: {auto_mode},\n"
                    #     f"5V Test Time in seconds: {loop_seconds},\n"
                    #     f"5V Test Range: {test_range} V,\n"
                    #     f"5V Test Value: {self.dmm_5V_reader.cget('text')},\n" 
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")

                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: 5V Test",
                                "item": "5V Test",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Test Time",
                                    "Upper Limit": upper_limit,
                                    "Lower Limit": lower_limit,
                                    "Reading": self.dmm_5V_reader.cget('text'),
                                    "Result": self.result_5v_test.cget('text')
                                }
                        }
                    )

                self.status_5v_test.config(fg="black")
                self.status_5v_test.grid()

                self.status_3_3v_test.config(fg="blue")
                self.status_3_3v_test.grid()

                if "3.3v_test" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    test_start_time = datetime.now()
                                    
                    logger.info(f"Start Time: {test_start_time}")
                            
                    logger.info("3.3V Test")
                    # self.datadog_logging("info","Start: 3.3V Test")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: 3.3V Test",
                                "item": "3.3V Test"
                        }
                    )
                    print("3.3V Test")
                    # Test Loop
                    self.submit_5V_dmm.config(state=tk.DISABLED)
                    # self.submit_3_3V_dmm.config(state=tk.NORMAL)
                    auto_mode = config.get("3.3v_test", "3.3v_test_auto_mode")
                    logger.info(f"3.3V Test Auto Mode: {auto_mode}")
                    print(f"3.3V Test Auto Mode: {auto_mode}")
                    loop_seconds = config.get("3.3v_test", "3.3v_test_duration_seconds")
                    logger.info(f"3.3V Test Time in seconds: {loop_seconds}")
                    print(f"3.3V Test Time in seconds: {loop_seconds}")
                    test_range = config.get("3.3v_test", "3.3v_test_range")
                    logger.info(f"3.3V Test Range: {test_range}")
                    print(f"3.3V Test Range: {test_range}")
                    
                    upper_limit = 3.3 + float(test_range)
                    lower_limit = 3.3 - float(test_range)
                    
                    self.range_value_3_3V_dmm.config( text=f"{test_range}", fg="black", font=("Helvetica", 10, "bold"))
                    if auto_mode =="True":
                        self.dmmReader.select_device(1)
                        self.dmm_reader_3_3V_value_manual(self.input_3_3V_dmm)
                    label_appear = True
                    start_time = time.time()
                    while time.time() - start_time < float(loop_seconds):
                        if label_appear == True:
                            self.status_3_3v_test.config(fg="blue")
                            self.status_3_3v_test.grid()
                            label_appear = False
                        else:
                            self.status_3_3v_test.config(fg="black")
                            self.status_3_3v_test.grid()
                            label_appear = True

                        if self.result_3_3v_test.cget("text") != "Not Yet":
                            break
                        time.sleep(0.5)
                    self.status_3_3v_test.config(fg="black")
                    self.status_3_3v_test.grid()
                    print(f"Device Voltage: {device_voltage}")

                    if device_voltage == "V":
                        print("3.3V Test: Failed")
                        test_result = "Failed"
                    else:
                        try:
                            device_voltage = float(self.input_3_3V_dmm.get())
                        except ValueError:
                            print("3.3 Test: Failed - Invalid Voltage Value")
                            test_result = "Failed"
                    
                    if self.dmm_3_3V_reader.cget("text") == "-":
                        self.result_3_3v_test.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("3.3V Test: Failed")
                        print("3.3V Test: Failed")
                        test_result = "Failed"

                        # disable_sticker_printing = 1
                    
                    elif self.result_3_3v_test.cget("text") == "Pass":
                        # self.result_3_3v_test.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("3.3V Test: Pass")
                        print("3.3V Test: Pass")
                        test_result = "Pass"    
                    
                    else:
                        # self.result_3_3v_test.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("3.3V Test: Pass")
                        # print("3.3V Test: Pass")
                        pass
                    
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: 3.3V Test,\n"
                    #     f"3.3V Test Auto Mode: {auto_mode},\n"
                    #     f"3.3V Test Time in seconds: {loop_seconds},\n"
                    #     f"3.3V Test Range: {test_range},\n"
                    #     f"3.3V Test Value: {self.dmm_3_3V_reader.cget('text')},\n" 
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: 3.3V Test",
                                "item": "3.3V Test",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Test Time",
                                    "Upper Limit": upper_limit,
                                    "Lower Limit": lower_limit,
                                    "Reading": self.dmm_3_3V_reader.cget('text'),
                                    "Result": self.result_3_3v_test.cget('text')
                                }
                        }
                    )

                self.status_3_3v_test.config(fg="black")
                self.status_3_3v_test.grid()

                self.status_atbeam_temp.config(fg="blue")
                self.status_atbeam_temp.grid()

                if "atbeam_temp" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""                
                    test_start_time = datetime.now() 
                    
                    logger.info(f"Start Time: {test_start_time}")

                    self.submit_3_3V_dmm.config(state=tk.DISABLED)

                    logger.info("Read ATBeam Temperature")
                    # self.datadog_logging("info","Start: Read ATBeam Temperature")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read ATBeam Temperature",
                                "item": "Temperature Test"
                        }
                    )
                    
                    print("Read ATBeam Temperature")
                    self.get_atbeam_temp()
                    # time.sleep(self.step_delay)
                    # self.datadog_logging("info","End: Read ATBeam Temperature")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "End: Read ATBeam Temperature",
                                "item": "Temperature Test"
                        }
                    )

                if "temp_compare" in config:
                    logger.info("Compare Temperature")
                    # self.datadog_logging("info","Start: Compare Temperature")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Compare Temperature",
                                "item": "Temperature Test"
                        }
                    )
                    print("Compare Temperature")
                    test_range = config.get("temp_compare", "temp_compare_range")
                    logger.info(f"Temperature Test Range: {test_range}")
                    print(f"Temperature Test Range: {test_range}")
                    
                    ext_sensor = self.aht20Sensor.read_temp_sensor()
                    ext_sensor = ext_sensor.strip()
                    array = ext_sensor.split(' ')
                    ext_sensor = float(array[0])
                    
                    #for upper and lower limit
                    ambient_temp = config.get("temp_compare", "ambient_temp")
                    upper_limit = str(float(ambient_temp) + float(test_range))
                    lower_limit = str(float(ambient_temp) - float(test_range))
                    
                    callibrated_ext_sensor = (0.9568*ext_sensor)-5.4626
                    raw_ext_sensor = ext_sensor
                    ext_sensor = callibrated_ext_sensor
                            
                    self.range_temp_value.config(text=f"{test_range}", fg="black", font=("Helvetica", 10, "bold"))
                    self.read_temp_aht20()

                    time.sleep(self.step_delay)

                    if self.result_temp_label.cget("text") == "Pass":
                        # self.result_temp_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Temperature Test: Pass")
                        print("Temperature Test: Pass")
                        test_result = "Pass"
                    else:
                        self.result_temp_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Temperature Test: Failed")
                        print("Temperature Test: Failed")
                        test_result = "Failed"

                        # disable_sticker_printing = 1
                        
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                    
                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Compare Temperature",
                                "item": "Temperature Test",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Compare Temperature",
                                    "Upper Limit": upper_limit,
                                    "Lower Limit": lower_limit,
                                    "Ambient Value": ambient_temp,
                                    "Test Range": test_range,
                                    "Device": f"{self.atbeam_temp_value.cget('text').split(' ')[0]} C",
                                    # "Ext Raw": f"{raw_ext_sensor} C",
                                    "Ext Raw": f"{self.ext_raw_temp_value.cget('text').split(' ')[2]} C",
                                    # "Ext Callibrated": f"{callibrated_ext_sensor} C",
                                    "Ext Callibrated": f"{self.ext_temp_value.cget('text').split(' ')[1]} C",
                                    "Result": test_result
                                }
                            }
                    )

                self.status_atbeam_temp.config(fg="black")
                self.status_atbeam_temp.grid()

                self.status_atbeam_humidity.config(fg="blue")
                self.status_atbeam_humidity.grid()

                if "atbeam_humid" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    test_start_time = datetime.now()          
                    
                    logger.info(f"Start Time: {test_start_time}")

                    logger.info("Read ATBeam Humidity")
                    # self.datadog_logging("info","Start: Read ATBeam Humidity")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read ATBeam Humidity",
                                "item": "Humidity Test"
                            }
                    )
                    print("Read ATBeam Humidity")
                    self.get_atbeam_humid()
                    # time.sleep(self.step_delay)
                    self.manual_test = True
                    # self.datadog_logging("info","End: Read ATBeam Humidity")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "End: Read ATBeam Humidity",
                                "item": "Humidity Test"
                            }
                    )

                if "humid_compare" in config:
                    logger.info("Compare Humidity")
                    # self.datadog_logging("info","Start: Compare Humidity")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Compare Humidity",
                                "item": "Humidity Test"
                        }
                    )
                    print("Compare Humidity")
                    test_range = config.get("humid_compare", "humid_compare_range")
                    logger.info(f"Humidity Test Range: {test_range}")
                    print(f"Humidity Test Time Range: {test_range}")
                    self.range_humid_value.config(text=f"{test_range}", fg="black", font=("Helvetica", 10, "bold"))
                    self.read_humid_aht20()

                    time.sleep(self.step_delay)
                    
                    ext_sensor = self.aht20Sensor.read_humid_sensor()
                    ext_sensor = ext_sensor.strip()
                    array = ext_sensor.split(' ')
                    ext_sensor = float(array[0])
                    
                    #for upper and lower limit
                    ambient_humid = config.get("humid_compare", "ambient_humid")
                    upper_limit = str(float(ambient_humid) + float(test_range))
                    lower_limit = str(float(ambient_humid) - float(test_range))
                    
                    callibrated_ext_sensor = (ext_sensor + 22)
                    raw_ext_sensor = ext_sensor
                    ext_sensor = callibrated_ext_sensor
                    
                    if self.result_humid_label.cget("text") == "Pass":
                        # self.result_humid_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Humidity Test: Pass")
                        print("Humidity Test: Pass")
                        test_result = "Pass"
                    else:
                        self.result_humid_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Humidity Test: Failed")
                        print("Humidity Test: Failed")
                        test_result = "Failed"

                        # disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Compare Humidity,\n"
                    #     f"Humidity Test Range: {test_range},\n"
                    #     f"Device Humidity: {self.atbeam_humid_value.cget('text').split(' ')[0]} %,\n"
                    #     f"External Humidity: {ext_sensor} %,\n"
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")         

                    self.datadog_logging(
                            "info" if test_result == "Pass" else "error",
                            {
                                    "summary": "End: Compare Humidity",
                                    "item": "Humidity Test",
                                    "start_time": str(test_start_time),
                                    "end_time": str(end_time),
                                    "duration": str(duration),
                                    "details": {
                                        "Action": "Humidity Test",
                                        "Upper Limit": upper_limit,
                                        "Lower Limit": lower_limit,
                                        "Ambient Value": ambient_humid,
                                        "Test Range": test_range,
                                        "Device": f"{self.atbeam_humid_value.cget('text').split(' ')[0]} %",
                                        # "Ext Raw": f"{raw_ext_sensor} %",
                                        "Ext Raw": f"{self.ext_raw_humid_value.cget('text').split(' ')[2]} %",
                                        # "Ext Callibrated": f"{callibrated_ext_sensor} %",
                                        "Ext Callibrated": f"{self.ext_humid_value.cget('text').split(' ')[1]} %",
                                        "Result": test_result
                                    }
                            }
                        )

                self.status_atbeam_humidity.config(fg="black")
                self.status_atbeam_humidity.grid()

                self.status_test_irrx.config(fg="blue")
                self.status_atbeam_humidity.grid()

                if "ir_receiver" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    test_start_time = datetime.now()         
                    
                logger.info(f"Start Time: {test_start_time}")
                      
                # self.datadog_logging("info","Start: IR Receiver Test")
                self.datadog_logging(
                    "info",
                    {
                            "summary": "Start: IR Receiver Test",
                            "item": "IR Receiver Test"
                    }
                )

                if self.result_factory_mode_label.cget("text") == "Pass":
                    # Test Loop
                    loop_seconds = config.get("ir_receiver", "ir_receive_test_duration_seconds")
                    logger.info(f"IR Receiver Test Time in seconds: {loop_seconds}")
                    print(f"IR Receiver Test Time in seconds: {loop_seconds}")

                    ir_receive = config.get("ir_receiver", "ir_receive_command")
                    ir_send = config.get("ir_receiver", "ir_send_command")
                    self.send_command(ir_receive + "\r\n")
                    time.sleep(self.step_delay)
                    self.send_command(ir_send + "\r\n")
                    # time.sleep(self.step_delay)
                    start_time = time.time()
                
                    # Set the label to blue and enable the button

                    # Run the loop for the specified duration
                    while time.time() - start_time < float(loop_seconds):
                        if self.result_test_irrx.cget("text") == "Pass":
                            logger.info("IR Receiver: Pass")
                            print("IR Receiver: Pass")
                            test_result = "Pass"
                            break
                        elif self.result_test_irrx.cget("text") == "Failed":
                            logger.info("IR Receiver: Failed")
                            print("IR Receiver: Failed")
                            test_result = "Failed"

                            disable_sticker_printing = 1

                            break

                        if self.stop_event.is_set():
                            logger.info("System Force Stop")
                            # self.datadog_logging("error","System Force Stop")
                            self.datadog_logging(
                                "error",
                                {
                                        "summary": "System Force Stop"
                                }
                            )
                            print("System Force Stop")
                            self.handle_exit_correctly()
                            time.sleep(2)
                            messagebox.showerror("Error", "System Force Stop")
                            return True

                        time.sleep(1)
                        
                    if self.result_test_irrx.cget("text") == "Not Yet":
                        # self.result_test_irrx.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_test_irrx.config(text="Pass", fg="green", font=("Helvetica", 10, "bold")) #temporary | Anuar
                        test_result = "Failed"
                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: IR Receiver Test,\n"
                    #     f"IR Receiver Test Time in seconds: {loop_seconds},\n"
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                        
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")                    
                    self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: IR Receiver Test",
                                "item": "IR Receiver Test",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Test Time",
                                    "Reading": loop_seconds,
                                    "Result": test_result
                                }
                        }
                    )
                            
                self.status_test_irrx.config(fg="black")
                self.status_atbeam_humidity.grid()

                # self.handle_exit_correctly()
                # messagebox.showerror("Error", "Test Stop!")
                # return True
        
                self.status_group2_factory_mode.config(fg="blue")
                self.status_group2_factory_mode.grid()

                logger.info("close_serial_port")
                # self.datadog_logging("info","close_serial_port")
                self.datadog_logging(
                    "info",
                    {
                            "summary": "close_serial_port"
                        }
                )
                print("close_serial_port")
                self.close_serial_port()

                logger.info("Increase Factory Mode Counter")
                self.datadog_logging(
                    "info",
                    {
                            "summary": "Increase Factory Mode Counter"
                    }
                )
                
                print("Increase Factory Mode Counter")
                self.serialCom.increase_factory_mode_counter()
                
                if "factory_esp32s3" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""          
                    
                    test_start_time = datetime.now()
                
                    logger.info(f"Start Time: {test_start_time}")

                    logger.info("Entering factory mode")

                    # self.datadog_logging("info","Start: Entering factory mode")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Entering factory mode",
                                "item": "Factory mode"
                            }
                    )
                
                    print("Entering factory mode")

                    # try:
                    esp32s3_port = self.port_var.get()
                    # esp32s3_port = "/dev/ttyACM0"
                    esp32s3_baud = int(self.baud_var.get())

                    esp32s3_factory_port = self.port_var1.get()
                    esp32s3_factory_baud = int(self.baud_var1.get())

                    esp32h2_port = self.port_var2.get()
                    esp32h2_baud = int(self.baud_var2.get())

                    if self.stop_event.is_set():
                        logger.info("System Force Stop")
                        # self.datadog_logging("error","System Force Stop")
                        self.datadog_logging(
                            "error",
                            {
                                    "summary": "System Force Stop"
                            }
                        )
                        print("System Force Stop")
                        self.handle_exit_correctly()
                        time.sleep(2)
                        messagebox.showerror("Error", "System Force Stop")
                        return True

                    logger.info("Open esp32s3 Factory Port")
                    print("Open esp32s3 Factory Port")
                    logger.info(f"factory Port: {esp32s3_factory_port}, Baud: {esp32s3_factory_baud}")
                    # self.datadog_logging(
                    #     "info",
                    #     f"Open esp32s3 Factory Port,\n" 
                    #     f"factory Port: {esp32s3_factory_port},\n" 
                    #     f"Baud: {esp32s3_factory_baud}"
                    # )
                    
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Open ESP32S3 Factory Port",
                                "item": "Factory mode"
                        }
                    )
                    
                    if self.serialCom.open_serial_port(esp32s3_factory_port, esp32s3_factory_baud):
                        self.handle_exit_correctly()
                        logger.info("Failed to open esp32s3 factory port")
                        # self.datadog_logging("error","Failed to open esp32s3 factory port")
                        self.datadog_logging(
                            "error",
                            {
                                    "summary": "Failed to open esp32s3 factory port",
                                    "item": "Factory mode"
                            }
                        )
                        print("Failed to open esp32s3 factory port")
                        messagebox.showerror("Error", "Failed to open esp32s3 factory port")
                        return True

                    logger.info("Reboot esp32s3 and esp32h2")
                    print("Reboot esp32s3 and esp32h2")
                    logger.info(f"Reboot esp32s3, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
                    logger.info(f"Reboot esp32h2, Port: {esp32h2_port}, Baud: {esp32h2_baud}")
                    self.reboot_h2(True, esp32h2_port, esp32h2_baud)
                    self.reboot_s3(False, True, esp32s3_port, esp32s3_baud)
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")  

                    self.datadog_logging(
                            "info",
                            {
                                    "summary": "End: Entering factory mode",
                                    "item": "Factory mode",
                                    "start_time": str(test_start_time),
                                    "end_time": str(end_time),
                                    "duration": str(duration),
                                    "details": {
                                        "Reboot ESP32S3": f"Port: {esp32s3_port}, Baud: {esp32s3_baud}",
                                        "Reboot ESP32H2": f"Port: {esp32h2_port} Baud: {esp32h2_baud}"
                                    }
                            }
                        )


                    logger.info("Start Wait 3")
                    print("Start Wait 3")
                    time.sleep(3)
                    logger.info("Finish Wait 3")
                    print("Finish Wait 3")

                    # except configparser.NoOptionError:
                    #     logger.error("Port not found in the INI file")
                    #     print("Port not found in the INI file")

                if "read_mac_address" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                                
                    logger.info("Read MAC Address")
                    # self.datadog_logging("info","Start: Read MAC Address")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Read Device MAC",
                                "item": "Read Device MAC"
                        }
                    )
                    print("Read MAC Address")
                    # self.get_device_mac()
                    command = config.get("read_mac_address", "read_mac_address_command")
                    self.send_command(command + "\r\n")
                    logger.info(f"Read MAC Address Command: {command}")
                    print(f"Read MAC Address Command: {command}")
                    logger.info(f"Reference MAC Address: {macAddress_esp32s3_data}")
                    print(f"Reference MAC Address: {macAddress_esp32s3_data}")
                    time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond
                    
                    # This is to update ui if the device successfully enter into factory mode
                    if self.result_group2_factory_mode.cget("text") == "Not Yet":
                        self.result_group2_factory_mode.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                    else:
                        pass
                    
                    # self.datadog_logging(
                    #     "info" if self.result_group2_factory_mode.cget("text") == "Pass" else "error",
                    #     f"End: Read MAC Address,\n"
                    #     f"Read MAC Address Command: {command},\n"
                    #     f"Reference MAC Address: {macAddress_esp32s3_data},\n"
                    #     f"Device MAC Address: {self.read_device_mac.cget('text')},\n"
                    #     f"Result: {self.result_group2_factory_mode.cget('text')}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                    self.datadog_logging(
                            "info" if self.result_group2_factory_mode.cget("text") == "Pass" else "error",
                            {
                                    "summary": "End: Read Device MAC",
                                    "item": "Read Device MAC",
                                    "start_time": str(test_start_time),
                                    "end_time": str(end_time),
                                    "duration": str(duration),
                                    "details": {
                                        "Action": "Read MAC Address",
                                        "Command": command,
                                        "Reference": macAddress_esp32s3_data,
                                        "Actual": self.read_device_mac.cget('text'),
                                        "Result": test_result
                                    }
                            }
                        )

                self.status_group2_factory_mode.config(fg="black")
                self.status_group2_factory_mode.grid()

                self.status_group2_wifi_softap_label.config(fg="blue")
                self.status_group2_wifi_softap_label.grid()
                
                # if "factory_reset" in config:
                #     logger.info("Reset the device to factory mode")
                #     print("Reset the device to factory mode")
                #     command = config.get("factory_reset", "factory_reset_command")
                #     self.send_command(command + "\r\n")
                #     logger.info(f"Factory Reset Command: {command}")
                #     print(f"Factory Reset Command: {command}")
                #     time.sleep(self.step_delay) # This delay is to allow so time for serial com to respond

                if "wifi_softap" in config:                                
                    # self.factory_flag = self.serialCom.device_factory_mode
                    # self.factory_flag = True
                    logger.debug(f"Factory Flag: {self.factory_flag}")
                    # time.sleep(3)
                    logger.info("Start Wi-Fi Soft AP Test")
                    # self.datadog_logging("info","Start: Wi-Fi Soft AP Test")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Wi-Fi Soft AP",
                                "item": "Wi-Fi Soft AP"
                            }
                    )
                    print("Start Wi-Fi Soft AP Test")
                    test_range = config.get("wifi_softap", "wifi_softap_test_rssi_range")
                    logger.info(f"Wi-Fi SoftAP RSSI Test Range: {test_range}")
                    print(f"Wi-Fi SoftAP RSSI Time Range: {test_range}")
                    self.range_group2_wifi_softap_rssi.config(text=f"{test_range} dBm", fg="black", font=("Helvetica", 10, "bold"))
                    self.wifi_scanning(test_range)
                    time.sleep(self.step_delay)
                    if self.result_group2_wifi_softap.cget("text") == "Pass":
                        # self.result_group2_wifi_softap_rssi.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Wi-Fi Soft AP: Pass")
                        print("Wi-Fi Soft AP: Pass")
                    else:
                        self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Wi-Fi Soft AP: Failed")
                        print("Wi-Fi Soft AP: Failed")

                        disable_sticker_printing = 1

                self.status_group2_wifi_softap_label.config(fg="black")
                self.status_group2_wifi_softap_label.grid()

                self.status_group2_wifi_station.config(fg="blue")
                self.status_group2_wifi_station.grid()

                if "wifi_station" in config:
                    logger.info("Start Wi-Fi Station Test")
                    # self.datadog_logging("info","Start: Wi-Fi Station Test")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Wi-Fi Station",
                                "item": "Wi-Fi Station"
                            }
                    )
                    print("Start Wi-Fi Station Test")
                    test_range = config.get("wifi_station", "wifi_station_test_rssi_range")
                    wifi_ssid_command = config.get("wifi_station", "wifi_station_inputssid_command")
                    logger.info(f"Wi-Fi Station RSSI Test Range: {test_range}")
                    print(f"Wi-Fi Station RSSI Time Range: {test_range}")
                    self.range_group2_wifi_station_rssi.config(text=f"{test_range} dBm", fg="black", font=("Helvetica", 10, "bold"))
                    self.send_command(wifi_ssid_command + "\r\n")
                    logger.info(f"Wi-Fi Station Command: {wifi_ssid_command}")
                    print(f"Wi-Fi Station Command: {wifi_ssid_command}")
                    time.sleep(3)
                    # wifi_pass_command = config.get("wifi_station", "wifi_station_inputpassword_command")
                    # logger.info(f"Wi-Fi Station Command: {wifi_pass_command}")
                    # print(f"Wi-Fi Station Command: {wifi_pass_command}")
                    # self.send_command(wifi_pass_command + "\r\n")
                    # time.sleep(3)
                    connect_wifi_command = config.get("wifi_station" , "wifi_station_connectwifi_command")
                    self.send_command(connect_wifi_command + "\r\n")
                    logger.info(f"Wi-Fi Station Command: {connect_wifi_command}")
                    print(f"Wi-Fi Station Command: {connect_wifi_command}")
                    time.sleep(10) #Allow time for the device to connect to wifi
                    wifi_rssi_command = config.get("wifi_station" , "wifi_station_rssi_command")
                    self.send_command(wifi_rssi_command + "\r\n")
                    logger.info(f"Wi-Fi Station RSSI Command: {wifi_rssi_command}")
                    print(f"Wi-Fi Station RSSI Command: {wifi_rssi_command}")
                    time.sleep(2)
                    self.get_atbeam_rssi(test_range)
                    time.sleep(5)
                    if self.result_group2_wifi_station.cget("text") == "Pass":
                        # self.result_group2_wifi_station.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Wi-Fi Station: Pass")
                        print("Wi-Fi Station: Pass")
                    else:
                        self.result_group2_wifi_station.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Wi-Fi Station: Failed")
                        print("Wi-Fi Station: Failed")

                        disable_sticker_printing = 1

                    self.status_group2_wifi_station.config(fg="black")
                    self.status_group2_wifi_station.grid()

                    self.status_http_device_matter_discriminator.config(fg="blue")
                    self.status_http_device_matter_discriminator.grid()

                    if self.result_group2_factory_mode.cget("text") == "Pass" and self.result_group2_wifi_station.cget("text") == "Pass":
                        test_start_time = ""
                        end_time = ""
                        duration = ""
                        
                        test_start_time = datetime.now()
                        
                        logger.info(f"Start Time: {test_start_time}")
                    
                        device_ip_address = self.extract_ip_from_dnsmasq_leases("/var/lib/misc/dnsmasq.leases","espressif")
                        print(f"IP address for {serialID_data}: {device_ip_address}")
                        if device_ip_address:
                            logger.info(f"IP address for {serialID_data}: {device_ip_address}")
                            # self.datadog_logging("info",f"IP address for {serialID_data}: {device_ip_address}")
                            self.datadog_logging(
                                "info",
                                {
                                        "summary": f"IP address for {serialID_data}",
                                        "item": "HTTP Device Matter Discriminator",
                                        "start_time": str(test_start_time),
                                        "details": {
                                            "IP address": device_ip_address
                                    }
                                }
                            )
                            print(f"IP address for {serialID_data}: {device_ip_address}")

                            try:
                                device_current_state_json = self.simple_httpc2device_current_state(f"{device_ip_address}")
                            except Exception as e:
                                logger.info(f"Fail to establish HTTP")
                                # self.datadog_logging("error","Fail to establish HTTP")
                                self.datadog_logging(
                                    "error",
                                    {
                                            "summary": "Fail to establish HTTP",
                                            "item": "HTTP Device Matter Discriminator"
                                }
                                )
                                print(f"Fail to establish HTTP")
                                self.result_http_device_matter_discriminator.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

                                disable_sticker_printing = 1
                            else:
                                json_data = json.loads(device_current_state_json)
                                matter_discriminator = json_data["info"]["internal"]
                                logger.info(f"Device Matter discriminator = {matter_discriminator}")
                                print(f"Device Matter discriminator = {matter_discriminator}")
                                self.http_device_matter_discriminator.config(text=f"{matter_discriminator}", fg="black", font=("Helvetica", 10, "bold"))

                                if matter_discriminator == discriminator_data:
                                    logger.info("Device matter discriminator is correct")
                                    # self.datadog_logging("info","Device matter discriminator is correct")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Device matter discriminator is correct",
                                                "item": "HTTP Device Matter Discriminator"
                                        }
                                    )
                                    print("Device matter discriminator is correct")
                                    self.result_http_device_matter_discriminator.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                                else:
                                    logger.info("Device matter discriminator is WRONG!!!")
                                    # self.datadog_logging("error","Device matter discriminator is WRONG!!!")
                                    self.datadog_logging(
                                        "error",
                                        {
                                                "summary": "Device matter discriminator is WRONG!!!",
                                                "item": "HTTP Device Matter Discriminator"
                                            }
                                    )
                                    print("Device matter discriminator is WRONG!!!")
                                    self.result_http_device_matter_discriminator.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

                                    # self.result_flashing_cert_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                                    # self.handle_exit_correctly()
                                    logger.info("Failed to flash ESP32S3 DAC")
                                    # print("Failed to flash ESP32S3 DAC")
                                    # messagebox.showerror("Error", "Fail to flash ESP32S3 DAC, Please make sure the port is correct.")
                                    # return True

                                    disable_sticker_printing = 1

                        else:
                            logger.info(f"Device {serialID_data} not found")
                            # self.datadog_logging("error",f"Device {serialID_data} not found")
                            self.datadog_logging(
                                "error",
                                {
                                        "summary": f"Device {serialID_data} not found",
                                        "item": "HTTP Device Matter Discriminator"
                                }
                            )
                            print(f"Device {serialID_data} not found")
                            self.result_http_device_matter_discriminator.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

                            disable_sticker_printing = 1
                    else:
                        logger.info("Device wifi station test failed!!!")
                        # self.datadog_logging("error","Device wifi station test failed!!!")
                        self.datadog_logging(
                            "error",
                            {
                                    "summary": "Device wifi station test failed!!!",
                                    "item": "HTTP Device Matter Discriminator"
                            }
                        )
                        print("Device wifi station test failed!!!")
                        self.result_http_device_matter_discriminator.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

                        disable_sticker_printing = 1
                        
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")                    
                    self.datadog_logging(
                            "info" if self.result_http_device_matter_discriminator.cget("text") == "Pass" else "error",
                            {
                                    "summary": "End: HTTP Device Matter Discriminator",
                                    "item": "HTTP Device Matter Discriminator",
                                    "start_time": str(test_start_time),
                                    "end_time": str(end_time),
                                    "duration": str(duration),
                                    "details": {
                                        "IP address": device_ip_address,
                                        "Matter Discriminator": matter_discriminator,
                                        "Result": self.result_http_device_matter_discriminator.cget("text")
                                    }
                            }
                        )

                self.status_http_device_matter_discriminator.config(fg="black")
                self.status_http_device_matter_discriminator.grid()
                
                # Edit by Anuar - 2024-10-21
                # Change button tets from timeout to fail
                # if "button" in config:
                #     logger.info("Button Test")
                #     print("Button Test")
                #     # self.button_fail_button.config(state=tk.NORMAL)
                #     # Test Loop
                #     loop_seconds = config.get("button", "button_test_duration_seconds")
                #     logger.info(f"Button Test Time in seconds: {loop_seconds}")
                #     print(f"Button Test Time in seconds: {loop_seconds}")
                #     label_appear = True
                #     start_time = time.time()
                #     while time.time() - start_time < float(loop_seconds):
                #     # while True:
                #         if label_appear == True:
                #             self.status_button_label.config(fg="blue")
                #             self.status_button_label.grid()
                #             self.button_fail_button.config(state=tk.NORMAL)
                #             self.add_image_next_to_frame()
                #             # self.instruction_button_label.grid(row=14, column=2, padx=5, pady=5, sticky=tk.W)
                #             label_appear = False
                #         else:
                #             self.status_button_label.config(fg="black")
                #             self.status_button_label.grid()
                #             # self.instruction_button_label.grid_forget()
                #             label_appear = True

                #         if self.result_button_label.cget("text") != "Not Yet":
                #             break
                #         time.sleep(0.5)
                #     self.status_button_label.config(fg="black")
                #     self.status_button_label.grid()
                #     # self.instruction_button_label.grid_forget()
                #     if self.result_button_label.cget("text") == "Pass":
                #         # self.result_button_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                #         self.button_fail_button.config(state=tk.DISABLED)
                #         logger.info("Button Test: Pass")
                #         print("Button Test: Pass")
                #     else:
                #         self.result_button_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                #         logger.info("Button Test: Failed")
                #         print("Button Test: Failed")
                #         self.button_fail_button.config(state=tk.DISABLED)
                #         # self.handle_exit_correctly()
                #         # messagebox.showerror("Error", "Button Test Failed!")
                #         # return True
            
            
                self.status_button_label.config(fg="blue")
                self.status_button_label.grid()
                
                # Edit by Anuar - 2024-10-21
                # Change button test from timeout to fail
                if "button" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                                
                    logger.info("Button Test")
                    # self.datadog_logging("info","Start: Button Test")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Button Test",
                                "item": "Button Test"
                            }
                    )
                    print("Button Test")

                    # Test Loop
                    loop_seconds = config.get("button", "button_test_duration_seconds")
                    logger.info(f"Button Test Time in seconds: {loop_seconds}")
                    print(f"Button Test Time in seconds: {loop_seconds}")

                    # start_time = time.time()
                    
                    # Set the label to blue and enable the button
                    
                    self.button_fail_button.config(state=tk.NORMAL)
                    self.add_image_next_to_frame()

                    # Run the loop for the specified duration
                    # while time.time() - start_time < float(loop_seconds):
                    while True:
                        if self.result_button_label.cget("text") != "Not Yet":
                            break

                        if self.stop_event.is_set():
                                logger.info("System Force Stop")
                                # self.datadog_logging("error","System Force Stop")
                                self.datadog_logging(
                                    "error",
                                    {
                                            "summary": "System Force Stop"
                                        }
                                )
                                print("System Force Stop")
                                self.handle_exit_correctly()
                                time.sleep(2)
                                messagebox.showerror("Error", "System Force Stop")
                                return True
                        time.sleep(1)

                    self.button_fail_button.config(state=tk.DISABLED)

                    # Handle test result
                    if self.result_button_label.cget("text") == "Pass":
                        logger.info("Button Test: Pass")
                        print("Button Test: Pass")
                        test_result = "Pass"
                    else:
                        self.result_button_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Button Test: Failed")
                        print("Button Test: Failed")
                        test_result = "Failed"

                        disable_sticker_printing = 1

                    yes_no_button_handling_sequence += 1
                    
                    # self.datadog_logging(
                    #     "info" if test_result == "Pass" else "error",
                    #     f"End: Button Test,\n"
                    #     f"Button Test Time in seconds: {loop_seconds},\n"
                    #     f"Result: {test_result}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                
                    logger.info(f"End Time: {end_time}")
                
                logger.info(f"Duration: {duration}")
                self.datadog_logging(
                        "info" if test_result == "Pass" else "error",
                        {
                                "summary": "End: Button Test",
                                "item": "Button Test",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Test Time",
                                    "Reading": loop_seconds,
                                    "Result": test_result
                                }
                        }
                    )

                # Reset status label appearance after the loop
                self.status_button_label.config(fg="black")
                self.status_button_label.grid()

                if "manual_test" in config:
                    
                    # self.datadog_logging("info","Start: Manual Test")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Manual Test",
                                "item": "Manual Test"
                            }
                    )
                    
                    self.image_added_red = False
                    self.image_added_green = False
                    self.image_added_blue = False
                    self.image_added_irrx = False
                    self.image_added_ir1 = False
                    self.image_added_ir2 = False
                    self.image_added_ir3 = False
                    self.image_added_ir4 = False
                    self.image_added_ir5 = False
                    
                    if self.result_factory_mode_label.cget("text") == "Pass":
                        redLed = config.get("manual_test", "redLed_command")
                        greenLed = config.get("manual_test", "greenLed_command")
                        blueLed = config.get("manual_test", "blueLed_command")
                        offLed = config.get("manual_test", "offLed_command")
                        ir_send = config.get("manual_test", "ir_send_command")
                        loop_seconds = config.get("manual_test", "manual_test_duration_seconds")
                        logger.info(f"Manual Test Time in seconds: {loop_seconds}")
                        print(f"Manual Test Time in seconds: {loop_seconds}")
                        logger.debug(f"Red LED: {redLed}, Green LED: {greenLed}, Blue LED: {blueLed}, IR Send: {ir_send}")
                        logger.info("Manual Test Loop Start")
                        print("Manual Test Loop Start")
                        # self.enable_frame(self.group3_frame)
                        step_counter = 0
                        start_time = time.time()
                        # Manual test loop
                        # while time.time() - start_time < float(loop_seconds):
                        while True:
                            # if self.manual_test and self.factory_flag == True:
                            #     logger.debug(self.factory_flag)
                            match step_counter:
                                case 0:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""     
                                    
                                    test_start_time = datetime.now()
                                
                                    logger.info(f"Start Time: {test_start_time}")

                                    # self.datadog_logging("info","Start: Red LED Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: Red LED",
                                                "item": "Red LED"
                                            }
                                    )

                                    if self.result_rgb_red_label.cget("text") == "Not Yet":
                                        self.status_rgb_red_label.config(fg="blue")
                                        self.status_rgb_red_label.grid()
                                        self.yes_button_red.config(state=tk.NORMAL)
                                        self.no_button_red.config(state=tk.NORMAL)
                                        if not self.image_added_red:
                                            self.add_image_next_to_frame()
                                            self.image_added_red = True
                                        self.send_command(redLed + "\r\n")
                                        # time.sleep(1)
                                    elif self.result_rgb_red_label.cget("text") == "Pass":
                                        logger.info("Red LED: Pass")
                                        print("Red LED: Pass")
                                        self.status_rgb_red_label.config(fg="black")
                                        self.status_rgb_red_label.grid()
                                        self.yes_button_red.config(state=tk.DISABLED)
                                        self.no_button_red.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_rgb_red_label.cget("text") == "Failed":
                                        logger.info("Red LED: Failed")
                                        print("Red LED: Failed")
                                        self.image_added_red = False 
                                        self.status_rgb_red_label.config(fg="black")
                                        self.status_rgb_red_label.grid()
                                        self.yes_button_red.config(state=tk.DISABLED)
                                        self.no_button_red.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                
                                    logger.info(f"End Time: {end_time}")
                                
                                    logger.info(f"Duration: {duration}")
                                    self.datadog_logging(
                                            "info" if self.result_rgb_red_label.cget("text") == "Pass" else "error",
                                            {
                                                    "summary": "End: Red LED",
                                                    "item": "Red LED",
                                                    "start_time": str(test_start_time),
                                                    "end_time": str(end_time),
                                                    "duration": str(duration),
                                                    "details": {
                                                        "Action": "Red LED",
                                                        "Command": redLed,
                                                        "Result": self.result_rgb_red_label.cget('text')
                                                        
                                                }
                                            }
                                        )

                                case 1:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""      
                                                
                                    test_start_time = datetime.now()
                                    
                                    logger.info(f"Start Time: {test_start_time}")
                                                    
                                    # self.datadog_logging("info","Start: Green LED Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: Green LED",
                                                "item": "Green LED"
                                            }
                                    )

                                    if self.result_rgb_green_label.cget("text") == "Not Yet":
                                        self.status_rgb_green_label.config(fg="blue")
                                        self.status_rgb_green_label.grid()
                                        self.yes_button_green.config(state=tk.NORMAL)
                                        self.no_button_green.config(state=tk.NORMAL)
                                        if self.image_added_green == False:
                                            self.add_image_next_to_frame()
                                            self.image_added_green = True
                                        self.send_command(greenLed + "\r\n")
                                        # time.sleep(1)
                                    elif self.result_rgb_green_label.cget("text") == "Pass":
                                        logger.info("Green LED: Pass")
                                        print("Green LED: Pass")
                                        self.status_rgb_green_label.config(fg="black")
                                        self.status_rgb_green_label.grid()
                                        self.yes_button_green.config(state=tk.DISABLED)
                                        self.no_button_green.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_rgb_green_label.cget("text") == "Failed":
                                        logger.info("Green LED: Failed")
                                        print("Green LED: Failed")
                                        self.image_added_green = False
                                        self.status_rgb_green_label.config(fg="black")
                                        self.status_rgb_green_label.grid()
                                        self.yes_button_green.config(state=tk.DISABLED)
                                        self.no_button_green.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    # self.datadog_logging(
                                    #     "info" if self.result_rgb_green_label.cget("text") == "Pass" else "error",
                                    #     f"End: Green LED Test,\n"
                                    #     f"Green LED Command: {greenLed},\n"
                                    #     f"Result: {self.result_rgb_green_label.cget('text')}"
                                    # )
                                    
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                    
                                    logger.info(f"End Time: {end_time}")
                                
                                    logger.info(f"Duration: {duration}") 

                                    self.datadog_logging(
                                            "info" if self.result_rgb_green_label.cget("text") == "Pass" else "error",
                                            {
                                                    "summary": "End: Green LED",
                                                    "item": "Green LED",
                                                    "start_time": str(test_start_time),
                                                    "end_time": str(end_time),
                                                    "duration": str(duration),
                                                    "details": {
                                                        "Action": "Green LED",
                                                        "Command": greenLed,
                                                        "Result": self.result_rgb_green_label.cget('text')
                                                }
                                            }
                                        )

                                case 2:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""      
                                    
                                    test_start_time = datetime.now() 
                                    
                                    logger.info(f"Start Time: {test_start_time}")
                                                                
                                    # self.datadog_logging("info","Start: Blue LED Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: Blue LED",
                                                "item": "Blue LED"
                                        }
                                    )

                                    if self.result_rgb_blue_label.cget("text") == "Not Yet":
                                        self.status_rgb_blue_label.config(fg="blue")
                                        self.status_rgb_blue_label.grid()
                                        self.yes_button_blue.config(state=tk.NORMAL)
                                        self.no_button_blue.config(state=tk.NORMAL)
                                        if self.image_added_blue == False:
                                            self.add_image_next_to_frame()
                                            self.image_added_blue = True
                                        self.send_command(blueLed + "\r\n")
                                        # time.sleep(1)
                                    elif self.result_rgb_blue_label.cget("text") == "Pass":
                                        logger.info("Blue LED: Pass")
                                        print("Blue LED: Pass")
                                        self.status_rgb_blue_label.config(fg="black")
                                        self.status_rgb_blue_label.grid()
                                        self.yes_button_blue.config(state=tk.DISABLED)
                                        self.no_button_blue.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_rgb_blue_label.cget("text") == "Failed":
                                        logger.info("Blue LED: Failed")
                                        print("Blue LED: Failed")
                                        self.image_added_blue = False
                                        self.status_rgb_blue_label.config(fg="black")
                                        self.status_rgb_blue_label.grid()
                                        self.yes_button_blue.config(state=tk.DISABLED)
                                        self.no_button_blue.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    # self.datadog_logging(
                                    #     "info" if self.result_rgb_blue_label.cget("text") == "Pass" else "error",
                                    #     f"End: Blue LED Test,\n"
                                    #     f"Blue LED Command: {blueLed},\n"
                                    #     f"Result: {self.result_rgb_blue_label.cget('text')}"
                                    # )
                                    
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                    
                                    logger.info(f"End Time: {end_time}")
                                
                                    logger.info(f"Duration: {duration}") 
                                                                
                                    self.datadog_logging(
                                            "info" if self.result_rgb_blue_label.cget("text") == "Pass" else "error",
                                            {
                                                    "summary": "End: Blue LED",
                                                    "item": "Blue LED",
                                                    "start_time": str(test_start_time),
                                                    "end_time": str(end_time),
                                                    "duration": str(duration),
                                                    "details": {
                                                        "Action": "Blue LED",
                                                        "Command": blueLed,
                                                        "Result": self.result_rgb_blue_label.cget('text')
                                                }
                                            }
                                        )

                                case 3:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""      
                                    
                                    test_start_time = datetime.now()
                                    
                                    logger.info(f"Start Time: {test_start_time}")
                                                                
                                    # self.datadog_logging("info","Start: Turn off LED Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: Off LED",
                                                "item": "Off LED"
                                            }
                                    )

                                    self.send_command(offLed + "\r\n") #The LED will be turn off by device when IR Rx is successful
                                    if self.result_rgb_off_label.cget("text") == "Not Yet":
                                        self.status_rgb_off_label.config(fg="blue")
                                        self.status_rgb_off_label.grid()
                                        self.yes_button_rgb_off.config(state=tk.NORMAL)
                                        self.no_button_rgb_off.config(state=tk.NORMAL)
                                        if self.image_added_irrx == False:
                                            self.add_image_next_to_frame()
                                            self.image_added_irrx = True
                                    elif self.result_rgb_off_label.cget("text") == "Pass":
                                        logger.info("Turn off LED: Pass")
                                        print("Turn off LED: Pass")
                                        self.status_rgb_off_label.config(fg="black")
                                        self.status_rgb_off_label.grid()
                                        self.yes_button_rgb_off.config(state=tk.DISABLED)
                                        self.no_button_rgb_off.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_rgb_off_label.cget("text") == "Failed":
                                        logger.info("Turn off LED: Failed")
                                        print("Turn off LED: Failed")
                                        self.status_rgb_off_label.config(fg="black")
                                        self.status_rgb_off_label.grid()
                                        self.yes_button_rgb_off.config(state=tk.DISABLED)
                                        self.no_button_rgb_off.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    # self.datadog_logging(
                                    #     "info" if self.result_rgb_off_label.cget("text") == "Pass" else "error",
                                    #     f"End: Turn off LED Test,\n"
                                    #     f"Turn off LED Command: {offLed},\n"
                                    #     f"Result: {self.result_rgb_off_label.cget('text')}"
                                    # )
                                    
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                    
                                    logger.info(f"End Time: {end_time}")
                
                                    logger.info(f"Duration: {duration}")
                                
                                    self.datadog_logging(
                                        "info" if self.result_rgb_off_label.cget("text") == "Pass" else "error",
                                        {
                                                "summary": "End: Off LED",
                                                "item": "Off LED",
                                                "start_time": str(test_start_time),
                                                "end_time": str(end_time),
                                                "duration": str(duration),
                                                "details": {
                                                    "Action": "Off LED",
                                                    "Command": offLed,
                                                    "Result": self.result_rgb_off_label.cget('text')
                                            }
                                        }
                                    )

                                case 4:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""      
                                    
                                    test_start_time = datetime.now()         
                                    
                                    logger.info(f"Start Time: {test_start_time}")

                                    # self.datadog_logging("info","Start: IR LED 1 Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: IR LED 1",
                                                "item": "IR LED 1"
                                        }
                                    )

                                    self.send_command(ir_send + "\r\n")
                                    if self.result_ir_led1.cget("text") == "Not Yet":
                                        self.ir_led1_label.config(fg="blue")
                                        self.ir_led1_label.grid()
                                        self.yes_button_ir_led1.config(state=tk.NORMAL)
                                        self.no_button_ir_led1.config(state=tk.NORMAL)
                                        if self.image_added_ir1 == False:
                                            self.add_image_next_to_frame()
                                            self.image_added_ir1 = True
                                    elif self.result_ir_led1.cget("text") == "Pass":
                                        logger.info("IR LED 1: Pass")
                                        print("IR LED 1: Pass")
                                        self.ir_led1_label.config(fg="black")
                                        self.ir_led1_label.grid()
                                        self.yes_button_ir_led1.config(state=tk.DISABLED)
                                        self.no_button_ir_led1.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_ir_led1.cget("text") == "Failed":
                                        logger.info("IR LED 1: Failed")
                                        print("IR LED 1: Failed")
                                        self.image_added_ir1 = False
                                        self.ir_led1_label.config(fg="black")
                                        self.ir_led1_label.grid()
                                        self.yes_button_ir_led1.config(state=tk.DISABLED)
                                        self.no_button_ir_led1.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    # self.datadog_logging(
                                    #     "info" if self.result_ir_led1.cget("text") == "Pass" else "error",
                                    #     f"End: IR LED 1 Test,\n"
                                    #     f"IR LED 1 Command: {ir_send},\n"
                                    #     f"Result: {self.result_ir_led1.cget('text')}"
                                    # )
                                    
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                    
                                    logger.info(f"End Time: {end_time}")
                
                                    logger.info(f"Duration: {duration}")
                                
                                    self.datadog_logging(
                                        "info" if self.result_ir_led1.cget("text") == "Pass" else "error",
                                        {
                                                "summary": "End: IR LED 1",
                                                "item": "IR LED 1",
                                                "start_time": str(test_start_time),
                                                "end_time": str(end_time),
                                                "duration": str(duration),
                                                "details": {
                                                    "Action": "IR LED 1",
                                                    "Command": ir_send,
                                                    "Result": self.result_ir_led1.cget('text')
                                            }
                                        }
                                    )

                                case 5:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""      
                                    
                                    test_start_time = datetime.now()      
                                    
                                    logger.info(f"Start Time: {test_start_time}")

                                    # self.datadog_logging("info","Start: IR LED 2 Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: IR LED 2",
                                                "item": "IR LED 2"
                                            }
                                    )

                                    self.send_command(ir_send + "\r\n")
                                    if self.result_ir_led2.cget("text") == "Not Yet":
                                        self.ir_led2_label.config(fg="blue")
                                        self.ir_led2_label.grid()
                                        self.yes_button_ir_led2.config(state=tk.NORMAL)
                                        self.no_button_ir_led2.config(state=tk.NORMAL)
                                        if self.image_added_ir2 == False:
                                            self.add_image_next_to_frame()
                                            self.image_added_ir2 = True
                                    elif self.result_ir_led2.cget("text") == "Pass":
                                        logger.info("IR LED 2: Pass")
                                        print("IR LED 2: Pass")
                                        self.ir_led2_label.config(fg="black")
                                        self.ir_led2_label.grid()
                                        self.yes_button_ir_led2.config(state=tk.DISABLED)
                                        self.no_button_ir_led2.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_ir_led2.cget("text") == "Failed":
                                        logger.info("IR LED 2: Failed")
                                        print("IR LED 2: Failed")
                                        self.image_added_ir2 = False
                                        self.ir_led2_label.config(fg="black")
                                        self.ir_led2_label.grid()
                                        self.yes_button_ir_led2.config(state=tk.DISABLED)
                                        self.no_button_ir_led2.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    # self.datadog_logging(
                                    #     "info" if self.result_ir_led2.cget("text") == "Pass" else "error",
                                    #     f"End: IR LED 2 Test,\n"
                                    #     f"IR LED 2 Command: {ir_send},\n"
                                    #     f"Result: {self.result_ir_led2.cget('text')}"
                                    # )
                                    
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                
                                    logger.info(f"End Time: {end_time}")
                
                                    logger.info(f"Duration: {duration}")

                                    self.datadog_logging(
                                        "info" if self.result_ir_led2.cget("text") == "Pass" else "error",
                                        {
                                                "summary": "End: IR LED 2",
                                                "item": "IR LED 2",
                                                "start_time": str(test_start_time),
                                                "end_time": str(end_time),
                                                "duration": str(duration),
                                                "details": {
                                                    "Action": "IR LED 2",
                                                    "Command": ir_send,    
                                                    "Result": self.result_ir_led2.cget('text')
                                                    }
                                        }
                                    )

                                case 6:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""      
                                    
                                    test_start_time = datetime.now()               
                                    
                                    logger.info(f"Start Time: {test_start_time}")

                                    # self.datadog_logging("info","Start: IR LED 3 Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: IR LED 3",
                                                "item": "IR LED 3"
                                            }
                                    )

                                    self.send_command(ir_send + "\r\n")
                                    if self.result_ir_led3.cget("text") == "Not Yet":
                                        self.ir_led3_label.config(fg="blue")
                                        self.ir_led3_label.grid()
                                        self.yes_button_ir_led3.config(state=tk.NORMAL)
                                        self.no_button_ir_led3.config(state=tk.NORMAL)
                                        if self.image_added_ir3 == False:
                                            self.add_image_next_to_frame()
                                            self.image_added_ir3 = True
                                    elif self.result_ir_led3.cget("text") == "Pass":
                                        logger.info("IR LED 3: Pass")
                                        print("IR LED 3: Pass")
                                        self.ir_led3_label.config(fg="black")
                                        self.ir_led3_label.grid()
                                        self.yes_button_ir_led3.config(state=tk.DISABLED)
                                        self.no_button_ir_led3.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_ir_led3.cget("text") == "Failed":
                                        logger.info("IR LED 3: Failed")
                                        print("IR LED 3: Failed")
                                        self.image_added_ir3 = False
                                        self.ir_led3_label.config(fg="black")
                                        self.ir_led3_label.grid()
                                        self.yes_button_ir_led3.config(state=tk.DISABLED)
                                        self.no_button_ir_led3.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    # self.datadog_logging(
                                    #     "info" if self.result_ir_led3.cget("text") == "Pass" else "error",
                                    #     f"End: IR LED 3 Test,\n"
                                    #     f"IR LED 3 Command: {ir_send},\n"
                                    #     f"Result: {self.result_ir_led3.cget('text')}"
                                    # )
                                    
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                    
                                    logger.info(f"End Time: {end_time}")
                
                                    logger.info(f"Duration: {duration}")
                                
                                    self.datadog_logging(
                                        "info" if self.result_ir_led3.cget("text") == "Pass" else "error",
                                        {
                                                "summary": "End: IR LED 3",
                                                "item": "IR LED 3",
                                                "start_time": str(test_start_time),
                                                "end_time": str(end_time),
                                                "duration": str(duration),
                                                "details": {
                                                    "Action": "IR LED 3",
                                                    "Command": ir_send,
                                                    "Result": self.result_ir_led3.cget('text')
                                            }
                                        }
                                    )

                                case 7:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""      
                                    
                                    test_start_time = datetime.now()   
                                    
                                    logger.info(f"Start Time: {test_start_time}")

                                    # self.datadog_logging("info","Start: IR LED 4 Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: IR LED 4",
                                                "item": "IR LED 4"
                                            }
                                    )

                                    self.send_command(ir_send + "\r\n")
                                    if self.result_ir_led4.cget("text") == "Not Yet":
                                        self.ir_led4_label.config(fg="blue")
                                        self.ir_led4_label.grid()
                                        self.yes_button_ir_led4.config(state=tk.NORMAL)
                                        self.no_button_ir_led4.config(state=tk.NORMAL)
                                        if self.image_added_ir4 == False:
                                            self.add_image_next_to_frame()
                                            self.image_added_ir4 = True                                
                                    elif self.result_ir_led4.cget("text") == "Pass":
                                        logger.info("IR LED 4: Pass")
                                        print("IR LED 4: Pass")
                                        self.ir_led4_label.config(fg="black")
                                        self.ir_led4_label.grid()
                                        self.yes_button_ir_led4.config(state=tk.DISABLED)
                                        self.no_button_ir_led4.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_ir_led4.cget("text") == "Failed":
                                        logger.info("IR LED 4: Failed")
                                        print("IR LED 4: Failed")
                                        self.image_added_ir4 = False
                                        self.ir_led4_label.config(fg="black")
                                        self.ir_led4_label.grid()
                                        self.yes_button_ir_led4.config(state=tk.DISABLED)
                                        self.no_button_ir_led4.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    # self.datadog_logging(
                                    #     "info" if self.result_ir_led4.cget("text") == "Pass" else "error",
                                    #     f"End: IR LED 4 Test,\n"
                                    #     f"IR LED 4 Command: {ir_send},\n"
                                    #     f"Result: {self.result_ir_led4.cget('text')}"
                                    # )
                                    
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                    
                                    logger.info(f"End Time: {end_time}")
                
                                    logger.info(f"Duration: {duration}")
                                
                                    self.datadog_logging(
                                        "info" if self.result_ir_led4.cget("text") == "Pass" else "error",
                                        {
                                                "summary": "End: IR LED 4",
                                                "item": "IR LED 4",
                                                "start_time": str(test_start_time),
                                                "end_time": str(end_time),
                                                "duration": str(duration),
                                                "details": {
                                                    "Action": "IR LED 4",
                                                    "Command": ir_send,
                                                    "Result": self.result_ir_led4.cget('text')
                                            }
                                        }
                                    )


                                case 8:
                                    test_start_time = ""
                                    end_time = ""
                                    duration = ""      
                                    
                                    test_start_time = datetime.now()    
                                    
                                    logger.info(f"Start Time: {test_start_time}")
                                                            
                                    # self.datadog_logging("info","Start: IR LED 5 Test")
                                    self.datadog_logging(
                                        "info",
                                        {
                                                "summary": "Start: IR LED 5",
                                                "item": "IR LED 5"
                                            }
                                    )

                                    self.send_command(ir_send + "\r\n")
                                    if self.result_ir_led5.cget("text") == "Not Yet":
                                        self.ir_led5_label.config(fg="blue")
                                        self.ir_led5_label.grid()
                                        self.yes_button_ir_led5.config(state=tk.NORMAL)
                                        self.no_button_ir_led5.config(state=tk.NORMAL)
                                        if self.image_added_ir5 == False:
                                            self.add_image_next_to_frame()
                                            self.image_added_ir5 = True                                
                                    elif self.result_ir_led5.cget("text") == "Pass":
                                        logger.info("IR LED 5: Pass")
                                        print("IR LED 5: Pass")
                                        self.ir_led5_label.config(fg="black")
                                        self.ir_led5_label.grid()
                                        self.yes_button_ir_led5.config(state=tk.DISABLED)
                                        self.no_button_ir_led5.config(state=tk.DISABLED)
                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                    elif self.result_ir_led5.cget("text") == "Failed":
                                        logger.info("IR LED 5: Failed")
                                        print("IR LED 5: Failed")
                                        self.image_added_ir5 = False
                                        self.ir_led5_label.config(fg="black")
                                        self.ir_led5_label.grid()
                                        self.yes_button_ir_led5.config(state=tk.DISABLED)
                                        self.no_button_ir_led5.config(state=tk.DISABLED)

                                        disable_sticker_printing = 1

                                        step_counter += 1
                                        yes_no_button_handling_sequence += 1
                                        
                                    # self.datadog_logging(
                                    #     "info" if self.result_ir_led5.cget("text") == "Pass" else "error",
                                    #     f"End: IR LED 5 Test,\n"
                                    #     f"IR LED 5 Command: {ir_send},\n"
                                    #     f"Result: {self.result_ir_led5.cget('text')}"
                                    # )
                                    
                                    end_time = datetime.now()
                                    
                                    duration = end_time - test_start_time
                                    
                                    logger.info(f"End Time: {end_time}")

                                    logger.info(f"Duration: {duration}")
                                
                                    self.datadog_logging(
                                        "info" if self.result_ir_led5.cget("text") == "Pass" else "error",
                                        {
                                                "summary": "End: IR LED 5",
                                                "item": "IR LED 5",
                                                "start_time": str(test_start_time),
                                                "end_time": str(end_time),
                                                "duration": str(duration),
                                                "details": {
                                                    "Action": "IR LED 5",
                                                    "Command": ir_send,
                                                    "Result": self.result_ir_led5.cget('text')
                                                }
                                        }
                                    )

                                case _: #this is a whildcard case, matching any other value
                                    break

                            if self.stop_event.is_set():
                                logger.info("System Force Stop")
                                # self.datadog_logging("error","System Force Stop")
                                self.datadog_logging(
                                    "error",
                                    {
                                            "summary": "System Force Stop"
                                        }  
                                )
                                print("System Force Stop")
                                self.handle_exit_correctly()
                                time.sleep(2)
                                messagebox.showerror("Error", "System Force Stop")
                                return True
                
                            if step_counter <= 2:
                                time.sleep(1)
                            elif step_counter >= 9:
                                time.sleep(1)
                            else:
                                time.sleep(2)

                            # else:
                            #     logger.error("Manual test loop not found in the INI file or conditions not met")
                            #     print("Manual test loop not found in the INI file or conditions not met")
                            #     break
                        self.yes_button_red.config(state=tk.DISABLED)
                        self.no_button_red.config(state=tk.DISABLED)
                        self.yes_button_green.config(state=tk.DISABLED)
                        self.no_button_green.config(state=tk.DISABLED)
                        self.yes_button_blue.config(state=tk.DISABLED)
                        self.no_button_blue.config(state=tk.DISABLED)
                        self.yes_button_rgb_off.config(state=tk.DISABLED)
                        self.no_button_rgb_off.config(state=tk.DISABLED)
                        self.yes_button_ir_led1.config(state=tk.DISABLED)
                        self.no_button_ir_led1.config(state=tk.DISABLED)
                        self.yes_button_ir_led2.config(state=tk.DISABLED)
                        self.no_button_ir_led2.config(state=tk.DISABLED)
                        self.yes_button_ir_led3.config(state=tk.DISABLED)
                        self.no_button_ir_led3.config(state=tk.DISABLED)
                        self.yes_button_ir_led4.config(state=tk.DISABLED)
                        self.no_button_ir_led4.config(state=tk.DISABLED)
                        self.yes_button_ir_led5.config(state=tk.DISABLED)
                        self.no_button_ir_led5.config(state=tk.DISABLED)

                        self.status_rgb_red_label.config(fg="black")
                        self.status_rgb_red_label.grid()
                        self.status_rgb_green_label.config(fg="black")
                        self.status_rgb_green_label.grid()
                        self.status_rgb_blue_label.config(fg="black")
                        self.status_rgb_blue_label.grid()
                        self.status_rgb_off_label.config(fg="black")
                        self.status_rgb_off_label.grid()
                        self.ir_led1_label.config(fg="black")
                        self.ir_led1_label.grid()
                        self.ir_led2_label.config(fg="black")
                        self.ir_led2_label.grid()
                        self.ir_led3_label.config(fg="black")
                        self.ir_led3_label.grid()
                        self.ir_led4_label.config(fg="black")
                        self.ir_led4_label.grid()
                        self.ir_led5_label.config(fg="black")
                        self.ir_led5_label.grid()

                        if self.result_rgb_red_label.cget("text") == "Pass":
                            # self.result_rgb_red_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("Red LED: Pass")
                            print("Red LED: Pass")
                        else:
                            self.result_rgb_red_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("Red LED: Failed")
                            print("Red LED: Failed")

                        if self.result_rgb_green_label.cget("text") == "Pass":
                            # self.result_rgb_green_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("Green LED: Pass")
                            print("Green LED: Pass")
                        else:
                            self.result_rgb_green_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("Green LED: Failed")
                            print("Green LED: Failed")

                        if self.result_rgb_blue_label.cget("text") == "Pass":
                            # self.result_rgb_blue_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("Blue LED: Pass")
                            print("Blue LED: Pass")
                        else:
                            self.result_rgb_blue_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("Blue LED: Failed")
                            print("Blue LED: Failed")

                        if self.result_rgb_off_label.cget("text") == "Pass":
                            # self.result_rgb_off_label.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("Off LED: Pass")
                            print("Off LED: Pass")
                        else:
                            self.result_rgb_off_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("Off LED: Failed")
                            print("Off LED: Failed")

                        if self.result_ir_led1.cget("text") == "Pass":
                            # self.result_ir_led1.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 1: Pass")
                            print("IR LED 1: Pass")
                        else:
                            self.result_ir_led1.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 1: Failed")
                            print("IR LED 1: Failed")

                        if self.result_ir_led2.cget("text") == "Pass":
                            # self.result_ir_led2.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 2: Pass")
                            print("IR LED 2: Pass")
                        else:
                            self.result_ir_led2.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 2: Failed")
                            print("IR LED 2: Failed")

                        if self.result_ir_led3.cget("text") == "Pass":
                            # self.result_ir_led3.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 3: Pass")
                            print("IR LED 3: Pass")
                        else:
                            self.result_ir_led3.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 3: Failed")
                            print("IR LED 3: Failed")

                        if self.result_ir_led4.cget("text") == "Pass":
                            # self.result_ir_led4.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 4: Pass")
                            print("IR LED 4: Pass")
                        else:
                            self.result_ir_led4.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 4: Failed")
                            print("IR LED 4: Failed")

                        if self.result_ir_led5.cget("text") == "Pass":
                            # self.result_ir_led5.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 5: Pass")
                            print("IR LED 5: Pass")
                        else:
                            self.result_ir_led5.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                            logger.info("IR LED 5: Failed")
                            print("IR LED 5: Failed")

                        logger.info("Manual Test Loop Completed")
                        
                        self.datadog_logging(
                            "info",
                            {
                                    "summary": "Manual Test Loop Completed",
                                    "item": "Manual Test"
                            }
                        )
                        print("Manual Test Loop Completed")
                    else:
                        self.result_rgb_red_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_rgb_green_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_rgb_blue_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_rgb_off_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_ir_def_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_ir_led1.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_ir_led2.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_ir_led3.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_ir_led4.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        self.result_ir_led5.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Manual Test Loop Failed")
                        # self.datadog_logging("error","Manual Test Loop Failed")
                        self.datadog_logging(
                            "error",
                            {
                                    "summary": "Manual Test Loop Failed",
                                    "item": "Manual Test"
                                }
                        )
                        
                        print("Manual Test Loop Failed")
                    time.sleep(self.step_delay)
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "End: Manual Test Loop",
                                "item": "Manual Test"
                            }
                    )


                if "esp32h2_header_pin" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""      
                    
                    test_start_time = datetime.now()     
                    
                    logger.info(f"Start Time: {test_start_time}")           
                
                    self.image_added_h2header = False
                    
                    logger.info("Short Header")
                    # self.datadog_logging("info","Start: Short Header")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Short Header",
                                "item": "Short Header"
                        }
                    )
                    print("Short Header")
                    # Test Loop
                    loop_seconds = config.get("esp32h2_header_pin", "esp32h2_header_pin_test_duration_seconds")
                    logger.info(f"Short Header Test Time in seconds: {loop_seconds}")
                    print(f"Short Header Test Time in seconds: {loop_seconds}")

                    self.yes_short_header.config(state=tk.NORMAL)
                    self.no_short_header.config(state=tk.NORMAL)
                    label_appear = True
                    start_time = time.time()
                    # while time.time() - start_time < float(loop_seconds):
                    while True:
                        if label_appear == True:
                            self.status_short_header.config(fg="blue")
                            self.status_short_header.grid()
                            if self.image_added_h2header == False:
                                self.add_image_next_to_frame()
                                self.image_added_h2header = True
                            label_appear = False
                        else:
                            self.status_short_header.config(fg="black")
                            self.status_short_header.grid()
                            label_appear = True

                        if self.result_short_header.cget("text") != "Not Yet":
                            break

                        if self.stop_event.is_set():
                                logger.info("System Force Stop")
                                # self.datadog_logging("error","System Force Stop")
                                self.datadog_logging(
                                    "error",
                                    {
                                            "summary": "System Force Stop"
                                    }
                                )
                                    
                                print("System Force Stop")
                                self.handle_exit_correctly()
                                time.sleep(2)
                                messagebox.showerror("Error", "System Force Stop")
                                return True
                        time.sleep(0.5)
                    self.status_short_header.config(fg="black")
                    self.status_short_header.grid()
                    if self.result_short_header.cget("text") == "Pass":
                        # self.result_short_header.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("Short Header: Pass")
                        print("Short Header: Pass")
                    else:
                        self.result_short_header.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("Short Header: Failed")
                        print("Short Header: Failed")

                        disable_sticker_printing = 1

                    self.yes_short_header.config(state=tk.DISABLED)
                    self.no_short_header.config(state=tk.DISABLED)
                    yes_no_button_handling_sequence += 1
                    
                    # self.datadog_logging(
                    #     "info" if self.result_short_header.cget("text") == "Pass" else "error",
                    #     f"End: Short Header Test,\n"
                    #     f"Test Time: {loop_seconds},\n"
                    #     f"Result: {self.result_short_header.cget('text')}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    self.datadog_logging(
                        "info" if self.result_short_header.cget("text") == "Pass" else "error",
                        {
                                "summary": "End: Short Header",
                                "item": "Short Header",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Test Time",
                                    "Reading": loop_seconds,
                                    "Result": self.result_short_header.cget('text')
                                }
                        }
                    )

                if "factory_esp32s3" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""      
                    
                    test_start_time = datetime.now()    

                    logger.info(f"Start Time: {test_start_time}")
                            
                    logger.info("Entering factory mode")
                    # self.datadog_logging("info","Start: Entering factory mode")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Entering factory mode",
                                "item": "Factory mode"
                            }
                    )
                    print("Entering factory mode")

                    # try:
                    esp32s3_port = self.port_var.get()
                    # esp32s3_port = "/dev/ttyACM0"
                    esp32s3_baud = int(self.baud_var.get())

                    esp32s3_factory_port = self.port_var1.get()
                    esp32s3_factory_baud = int(self.baud_var1.get())

                    esp32h2_port = self.port_var2.get()
                    esp32h2_baud = int(self.baud_var2.get())

                    if self.stop_event.is_set():
                        logger.info("System Force Stop")
                        # self.datadog_logging("error","System Force Stop")
                        self.datadog_logging(
                            "error",
                            {
                                    "summary": "System Force Stop"
                                }
                        )
                        print("System Force Stop")
                        self.handle_exit_correctly()
                        time.sleep(2)
                        messagebox.showerror("Error", "System Force Stop")
                        return True

                    logger.info("Reboot esp32s3 and esp32h2")
                    print("Reboot esp32s3 and esp32h2")
                    logger.info(f"Reboot esp32s3, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
                    logger.info(f"Reboot esp32h2, Port: {esp32h2_port}, Baud: {esp32h2_baud}")
                    self.reboot_h2(True, esp32h2_port, esp32h2_baud)
                    self.reboot_s3(False, True, esp32s3_port, esp32s3_baud)
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "End: Entering factory mode",
                                "item": "Factory mode",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Reboot ESP32S3": f"Port: {esp32s3_port}, Baud: {esp32s3_baud}",
                                    "Reboot ESP32H2": f"Port: {esp32h2_port} Baud: {esp32h2_baud}"
                                }
                        }
                    )


                    logger.info("Start Wait 3")
                    # print("Start Wait 3")
                    # time.sleep(3)
                    logger.info("Finish Wait 3")
                    # print("Finish Wait 3")

                    # except configparser.NoOptionError:
                    #     logger.error("Port not found in the INI file")
                    #     print("Port not found in the INI file")

                if "esp32h2_led" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""      
                    
                    test_start_time = datetime.now()            
                    
                    logger.info(f"Start Time: {test_start_time}")
                    
                    self.image_added_h2led = False
                    
                    logger.info("ESP32H2 LED Test")
                    # self.datadog_logging("info","Start: ESP32H2 LED Test")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: ESP32H2 Small LED Test",
                                "item": "ESP32H2 Small LED Test"
                            }
                    )

                    print("ESP32H2 LED Test")
                    # Test Loop
                    loop_seconds = config.get("esp32h2_led", "esp32h2_led_test_duration_seconds")
                    logger.info(f"ESP32H2 LED Test Time in seconds: {loop_seconds}")
                    print(f"ESP32H2 LED Test Time in seconds: {loop_seconds}")

                    self.yes_h2_led_check.config(state=tk.NORMAL)
                    self.no_h2_led_check.config(state=tk.NORMAL)
                    label_appear = True
                    start_time = time.time()
                    # while time.time() - start_time < float(loop_seconds):
                    while True:
                        if label_appear == True:
                            self.status_h2_led_check.config(fg="blue")
                            self.status_h2_led_check.grid()
                            if self.image_added_h2led == False:
                                self.add_image_next_to_frame()
                                self.image_added_h2led = True
                            label_appear = False
                        else:
                            self.status_h2_led_check.config(fg="black")
                            self.status_h2_led_check.grid()
                            label_appear = True

                        if self.result_h2_led_check.cget("text") != "Not Yet":
                            break

                        if self.stop_event.is_set():
                            logger.info("System Force Stop")
                            # self.datadog_logging("error","System Force Stop")
                            self.datadog_logging(
                                "error",
                                {
                                        "summary": "System Force Stop"
                                    }
                            )
                            print("System Force Stop")
                            self.handle_exit_correctly()
                            time.sleep(2)
                            messagebox.showerror("Error", "System Force Stop")
                            return True
                    
                        time.sleep(0.5)

                    self.status_h2_led_check.config(fg="black")
                    self.status_h2_led_check.grid()
                    if self.result_h2_led_check.cget("text") == "Pass":
                        # self.result_h2_led_check.config(text="Pass", fg="green", font=("Helvetica", 10, "bold"))
                        logger.info("ESP32H2 Small LED: Pass")
                        print("ESP32H2 Small LED: Pass")
                    else:
                        self.result_h2_led_check.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
                        logger.info("ESP32H2 Small LED: Failed")
                        print("ESP32H2 Small LED: Failed")

                        disable_sticker_printing = 1
                        
                    # self.datadog_logging(
                    #     "info" if self.result_h2_led_check.cget("text") == "Pass" else "error",
                    #     f"End: ESP32H2 LED Test,\n"
                    #     f"Test Time: {loop_seconds},\n"
                    #     f"Result: {self.result_h2_led_check.cget('text')}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                                
                    self.datadog_logging(
                        "info" if self.result_h2_led_check.cget("text") == "Pass" else "error",
                        {
                                "summary": "End: ESP32H2 Small LED Test",
                                "item": "ESP32H2 Small LED Test",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Test Time",
                                    "Reading": loop_seconds,
                                    "Result": self.result_h2_led_check.cget('text')
                                }
                        }
                    )

                    self.yes_h2_led_check.config(state=tk.DISABLED)
                    self.no_h2_led_check.config(state=tk.DISABLED)
                    yes_no_button_handling_sequence += 1

                if "print_sticker" in config:
                    test_start_time = ""
                    end_time = ""
                    duration = ""      
                    
                    test_start_time = datetime.now()
                    
                    logger.info(f"Start Time: {test_start_time}")
                
                    logger.info("Sticker Printing")
                    # self.datadog_logging("info","Start: Sticker Printing")
                    self.datadog_logging(
                        "info",
                        {
                                "summary": "Start: Sticker Printing",
                                "item": "Sticker Printing"
                            }
                    )
                    print("Sticker Printing")

                    if f"{orderNumber}" == "hand-sample" or f"{orderNumber}" == "200-trial-run":
                        self.print_option_response = tk.StringVar(value="single")
                        # self.print_option_response.set(value="single")
                    else:
                        self.print_option_response = tk.StringVar(value="double")
                        # self.print_option_response.set(value="double")
                    self.radio_single.config(variable=self.print_option_response)
                    self.radio_single.grid()
                    self.radio_double.config(variable=self.print_option_response)
                    self.radio_double.grid()

                    loop_seconds = config.get("print_sticker", "print_sticker_duration_seconds")
                    logger.info(f"Print Sticker Time in seconds: {loop_seconds}")
                    print(f"Print Sticker Time in seconds: {loop_seconds}")
                    auto_mode = config.get("print_sticker", "print_sticker_auto_mode")
                    logger.info(f"Print Sticker Auto Mode: {auto_mode}")
                    print(f"Print Sticker Auto Mode: {auto_mode}")

                    self.printer_qrpayload_data_label.config(text=f"{qrCode_data}")
                    self.printer_manualcode_data_label.config(text=f"{manualCode_data}")

                    if disable_sticker_printing == 1:
                        logger.info("Restricted From Printing Sticker")
                        # self.datadog_logging("error","Restricted From Printing Sticker")
                        self.datadog_logging(
                            "error",
                            {
                                    "summary": "Restricted From Printing Sticker",
                                    "item": "Sticker Printing"
                                }
                        )
                        print("Restricted From Printing Sticker")
                    else:
                        # Test Loop
                        self.printer_print.config(state=tk.NORMAL)
                        self.printer_no_print.config(state=tk.NORMAL)
                        if auto_mode == "True":
                            self.send_to_printer()
                        else:
                            pass
                        label_appear = True
                        start_time = time.time()
                        break_printer = 0
                        # while time.time() - start_time < float(loop_seconds):
                        while True:
                            if label_appear == True:
                                self.printer_label.config(fg="blue")
                                self.printer_label.grid()
                                label_appear = False
                            else:
                                self.printer_label.config(fg="black")
                                self.printer_label.grid()
                                label_appear = True

                            if break_printer == 1:
                                break
                            
                            if self.stop_event.is_set():
                                logger.info("System Force Stop")
                                # self.datadog_logging("error","System Force Stop")
                                self.datadog_logging(
                                    "error",
                                    {
                                            "summary": "System Force Stop"
                                    }
                                )
                                print("System Force Stop")
                                self.handle_exit_correctly()
                                time.sleep(2)
                                messagebox.showerror("Error", "System Force Stop")
                                return True
                            
                            time.sleep(0.5)
                        self.printer_label.config(fg="black")
                        self.printer_label.grid()
                        
                    # self.datadog_logging(
                    #     "error" if disable_sticker_printing == 1 else "info",
                    #     f"End: Sticker Printing,\n"
                    #     f"Test Time: {loop_seconds},\n"
                    #     f"Result: {'Restricted From Printing Sticker' if disable_sticker_printing == 1 else 'Printed Sticker'}"
                    # )
                    
                    end_time = datetime.now()
                    
                    duration = end_time - test_start_time
                    
                    logger.info(f"End Time: {end_time}")
                
                    logger.info(f"Duration: {duration}")
                
                    self.datadog_logging(
                        "error" if disable_sticker_printing == 1 else "info",
                        {
                                "summary": "End: Sticker Printing",
                                "item": "Sticker Printing",
                                "start_time": str(test_start_time),
                                "end_time": str(end_time),
                                "duration": str(duration),
                                "details": {
                                    "Action": "Test Time",
                                    "Reading": loop_seconds,
                                    "Result": "Restricted From Printing Sticker" if disable_sticker_printing == 1 else "Printed Sticker"
                                }
                            }    
                    )
            else:
                # self.result_read_device_mac = tk.Label(self.group1_frame, text="SKIP")
                self.result_read_device_mac.config(text="SKIP")
                self.result_read_device_mac.grid()

                # self.result_read_device_firmware_version = tk.Label(self.group1_frame, text="SKIP")
                self.result_read_device_firmware_version.config(text="SKIP")
                self.result_read_device_firmware_version.grid()

                # self.result_read_prod_name = tk.Label(self.group1_frame, text="SKIP")
                self.result_read_prod_name.config(text="SKIP")
                self.result_read_prod_name.grid()

                # self.result_write_serialnumber = tk.Label(self.group1_frame,text="SKIP")
                self.result_write_serialnumber.config(text="SKIP")
                self.result_write_serialnumber.grid()

                # self.result_read_device_matter_dac_vid = tk.Label(self.group1_frame, text="SKIP")
                self.result_read_device_matter_dac_vid.config(text="SKIP")
                self.result_read_device_matter_dac_vid.grid()

                # self.result_read_device_matter_dac_pid = tk.Label(self.group1_frame, text="SKIP")
                self.result_read_device_matter_dac_pid.config(text="SKIP")
                self.result_read_device_matter_dac_pid.grid()

                # self.result_read_device_matter_vid = tk.Label(self.group1_frame, text="SKIP")
                self.result_read_device_matter_vid.config(text="SKIP")
                self.result_read_device_matter_vid.grid()

                # self.result_read_device_matter_pid = tk.Label(self.group1_frame, text="SKIP")
                self.result_read_device_matter_pid.config(text="SKIP")
                self.result_read_device_matter_pid.grid()

                # self.result_read_device_matter_discriminator = tk.Label(self.group1_frame, text="SKIP")
                self.result_read_device_matter_discriminator.config(text="SKIP")
                self.result_read_device_matter_discriminator.grid()

                # self.result_write_mtqr = tk.Label(self.group1_frame, text="SKIP")
                self.result_write_mtqr.config(text="SKIP")
                self.result_write_mtqr.grid()

                # self.result_ir_def_label = tk.Label(self.group1_frame, text="SKIP")
                self.result_ir_def_label.config(text="SKIP")
                self.result_ir_def_label.grid()

                # self.result_save_device_data_label = tk.Label(self.group1_frame, text="SKIP")
                self.result_save_device_data_label.config(text="SKIP")
                self.result_save_device_data_label.grid()

                # self.result_save_application_data_label = tk.Label(self.group1_frame, text="SKIP")
                self.result_save_application_data_label.config(text="SKIP")
                self.result_save_application_data_label.grid()

                # self.result_5v_test = tk.Label(self.group1_frame, text="SKIP")
                self.result_5v_test.config(text="SKIP")
                self.result_5v_test.grid()

                # self.result_3_3v_test = tk.Label(self.group1_frame, text="SKIP")
                self.result_3_3v_test.config(text="SKIP")
                self.result_3_3v_test.grid()

                # self.result_temp_label = tk.Label(self.group1_frame, text="SKIP")
                self.result_temp_label.config(text="SKIP")
                self.result_temp_label.grid()

                # self.result_humid_label = tk.Label(self.group1_frame, text="SKIP")
                self.result_humid_label.config(text="SKIP")
                self.result_humid_label.grid()

                # self.result_test_irrx= tk.Label(self.group1_frame, text="SKIP")
                self.result_test_irrx.config(text="SKIP")
                self.result_test_irrx.grid()

                # self.result_group2_factory_mode = tk.Label(self.group2_frame, text="SKIP")
                self.result_group2_factory_mode.config(text="SKIP")
                self.result_group2_factory_mode.grid()

                # self.result_group2_wifi_softap = tk.Label(self.group2_frame, text="SKIP")
                self.result_group2_wifi_softap.config(text="SKIP")
                self.result_group2_wifi_softap.grid()

                # self.result_group2_wifi_station = tk.Label(self.group2_frame, text="SKIP")
                self.result_group2_wifi_station.config(text="SKIP")
                self.result_group2_wifi_station.grid()

                # self.result_http_device_matter_discriminator = tk.Label(self.group2_frame, text="SKIP")
                self.result_http_device_matter_discriminator.config(text="SKIP")
                self.result_http_device_matter_discriminator.grid()

                # self.result_button_label = tk.Label(self.group3_frame, text="SKIP")
                self.result_button_label.config(text="SKIP")
                self.result_button_label.grid()

                # self.result_rgb_red_label = tk.Label(self.group3_frame, text="SKIP")
                self.result_rgb_red_label.config(text="SKIP")
                self.result_rgb_red_label.grid()

                # self.result_rgb_green_label = tk.Label(self.group3_frame, text="SKIP")
                self.result_rgb_green_label.config(text="SKIP")
                self.result_rgb_green_label.grid()

                # self.result_rgb_blue_label = tk.Label(self.group3_frame, text="SKIP")
                self.result_rgb_blue_label.config(text="SKIP")
                self.result_rgb_blue_label.grid()

                # self.result_rgb_off_label = tk.Label(self.group3_frame, text="SKIP")
                self.result_rgb_off_label.config(text="SKIP")
                self.result_rgb_off_label.grid()

                # self.result_ir_led1 = tk.Label(self.group3_frame, text="SKIP")
                self.result_ir_led1.config(text="SKIP")
                self.result_ir_led1.grid()

                # self.result_ir_led2 = tk.Label(self.group3_frame, text="SKIP")
                self.result_ir_led2.config(text="SKIP")
                self.result_ir_led2.grid()

                # self.result_ir_led3 = tk.Label(self.group3_frame, text="SKIP")
                self.result_ir_led3.config(text="SKIP")
                self.result_ir_led3.grid()

                # self.result_ir_led4 = tk.Label(self.group3_frame, text="SKIP")
                self.result_ir_led4.config(text="SKIP")
                self.result_ir_led4.grid()

                # self.result_ir_led5 = tk.Label(self.group3_frame, text="SKIP")
                self.result_ir_led5.config(text="SKIP")
                self.result_ir_led5.grid()

                # self.result_short_header = tk.Label(self.group4_frame, text="SKIP")
                self.result_short_header.config(text="SKIP")
                self.result_short_header.grid()

                # self.result_h2_led_check = tk.Label(self.group4_frame, text="SKIP")
                self.result_h2_led_check.config(text="SKIP")
                self.result_h2_led_check.grid()

                logger.info("Skip All Testing")
                print("Skip All Testing")

                self.datadog_logging(
                    "info" if self.result_flashing_cert_label.cget("text") == "Completed" else "error",
                    {
                            "summary": "Skip All Testing"
                    }
                )
                
        global master_start_time
        global master_end_time
        global master_duration
        
        master_end_time = datetime.now()
        
        master_duration = master_end_time - master_start_time
        
        logger.info(f"Master End Time: {str(master_end_time)}")
        logger.info(f"Master Duration: {str(master_duration)}")
        
        self.datadog_logging(
            "info",
            {
                    "summary": "End: Master Test",
                    "start_time": str(master_start_time),
                    "end_time": str(master_end_time),
                    "duration": str(master_duration)
                }
        )

        self.handle_exit_correctly()

        if disable_sticker_printing == 1:
            logger.info("Test Result Contain Failure,")
            # self.datadog_logging("error","Test Result Contain Failure")
            self.datadog_logging(
                "error",
                {
                        "summary": "Test Result Contain Failure",
                        "item": "Sticker Printing"
                }
            )
            print("Test Result Contain Failure,")
            messagebox.showerror("Error", "Test Failed!")
        else:
            if check_esp32s3_module == 1:
                logger.info("Finish Check ESP32S3 Module")
                # self.datadog_logging("info","Finish Check ESP32S3 Module")
                self.datadog_logging(
                    "info",
                    {
                            "summary": "Finish Check ESP32S3 Module"
                    }
                )
                print("Finish Check ESP32S3 Module")
                messagebox.showinfo("Info", "Finish Check ESP32S3 Module")
            else:
                logger.info("Test 2 Completed")
                # self.datadog_logging("info","Test 2 Completed")
                self.datadog_logging(
                    "info",
                    {
                            "summary": "Test 2 Completed"
                    }   
                )
                print("Test 2 Completed")
                messagebox.showinfo("Information", "Test Completed")

        return False

    def start_task2_thread(self):
        self.task2_thread = threading.Thread(target=self.start_test2)
        self.task2_thread.start()
        print("start_task2_thread")
        return self.task2_thread
        # self.start_test2()

    def start_process(self):
        global retest_flag
        global flash_only_flag

        retest_flag = 0
        flash_only_flag = 0
        self.combine_tasks()

    def flash_process(self):
        global retest_flag
        global flash_only_flag

        retest_flag = 0
        flash_only_flag = 1
        self.combine_tasks()

    def retest_process(self):
        global retest_flag
        global flash_only_flag

        retest_flag = 1
        flash_only_flag = 0
        self.combine_tasks()

    def combine_tasks(self):
        global check_esp32s3_module
        global disable_sticker_printing

        selected_order_number = self.order_number_dropdown_list.get()
        if selected_order_number:

            disable_sticker_printing = 0

            sensor_file = f"{sensor_txt_fullpath}"
            if os.path.exists(sensor_file):
                os.remove(sensor_file)
                print(f"Removed ' {sensor_file} ' ")

            self.reset_ui()
            self.reset_tasks()

            self.disable_configurable_ui()

            self.clear_task_threads()

            task1_thread = self.start_task1_thread()

            task2_thread = self.start_task2_thread()

            print("System Stop and Ready for next action")
        else:
            messagebox.showwarning("Warning", "Select order number")

    def clear_task_threads(self):
        print("clear_task_threads") 
        # self.stop_event.set()  # Signal the threads to stop
        if self.task1_thread and self.task1_thread.is_alive():
            self.task1_thread.join(timeout=10)  # Add a timeout to join to prevent hanging
        if self.task2_thread and self.task2_thread.is_alive():
            self.task2_thread.join(timeout=10)  # Add a timeout to join to prevent hanging

    def reset_tasks(self):
        global yes_no_button_handling_sequence

        yes_no_button_handling_sequence = 0
        # self.clear_task_threads()
        self.task1_completed.clear()
        self.task1_thread_failed.clear()
        self.task2_thread_failed.clear()
        self.stop_event.clear()

        print("Reset Factory Mode Counter")
        self.serialCom.reset_factory_mode_counter()
        
    def reload_ir_thread_task(self):
        self.reload_ir_thread = Thread(target=self.reload_ir)
        self.reload_ir_thread.start()

    def reload_ir(self):
        print("Start Reload IR")
        
        self.initialize_serialCom(self.retest_label)
        # self.reset_ui()
        # self.reset_tasks()

        # self.clear_task_threads()
        # self.result_ir_def_label.grid_forget()
        
        ini_file_path = os.path.join(script_dir, ini_file_name)

        if not os.path.exists(ini_file_path):
            logger.error(f"{ini_file_name} not found in the specified directory: {script_dir}")
            
            self.datadog_logging(
                "error",
                {
                        "summary": f"{ini_file_name} not found in the specified directory: {script_dir}"
                }
            )
            
            print(f"{ini_file_name} not found in the specified directory: {script_dir}")
            return

        # Load the test script
        self.loadTestScript = LoadTestScript(ini_file_path)

        # Read INI configuration file
        config = configparser.ConfigParser()
        config.read(ini_file_path)
        
        # Handle Factory Mode configuration
        if "factory_esp32s3" in config:
            logger.info("Entering factory mode")
            # self.datadog_logging("info","Start: Entering factory mode")
            self.datadog_logging(
                "info",
                {
                        "summary": "Start: Entering factory mode"
                }
            )
            print("Entering factory mode")

            esp32s3_port = self.port_var.get()
            esp32s3_baud = int(self.baud_var.get())

            esp32s3_factory_port = self.port_var1.get()
            esp32s3_factory_baud = int(self.baud_var1.get())

            esp32h2_port = self.port_var2.get()
            esp32h2_baud = int(self.baud_var2.get())

            if self.stop_event.is_set():
                logger.info("System Force Stop")
                
                self.datadog_logging(
                    "error",
                    {
                            "summary": "System Force Stop"
                    }
                )
                
                print("System Force Stop")
                self.handle_exit_correctly()
                time.sleep(2)
                messagebox.showerror("Error", "System Force Stop")
                return True

            logger.info("Open ESP32S3 Factory Port")
            print("Open ESP32S3 Factory Port")
            logger.info(f"Factory Port: {esp32s3_factory_port}, Baud: {esp32s3_factory_baud}")
            
            self.datadog_logging(
                "info",
                {
                        "summary": "Open ESP32S3 Factory Port"
                }
            )
            
            if self.serialCom.open_serial_port(esp32s3_factory_port, esp32s3_factory_baud):
                self.handle_exit_correctly()
                logger.info("Failed to open ESP32S3 factory port")
                print("Failed to open ESP32S3 factory port")
                messagebox.showerror("Error", "Failed to open ESP32S3 factory port")
                return True

            logger.info("Reboot esp32s3 and esp32h2")
            print("Reboot esp32s3 and esp32h2")
            logger.info(f"Reboot esp32s3, Port: {esp32s3_port}, Baud: {esp32s3_baud}")
            logger.info(f"Reboot esp32h2, Port: {esp32h2_port}, Baud: {esp32h2_baud}")
            self.reboot_h2(True, esp32h2_port, esp32h2_baud)
            self.reboot_s3(False, True, esp32s3_port, esp32s3_baud)
            self.datadog_logging(
                "info",
                {
                        "summary": "End: Entering factory mode",
                            "details": {
                                "Reboot ESP32S3": f"Port: {esp32s3_port}, Baud: {esp32s3_baud}",
                                "Reboot ESP32H2": f"Port: {esp32h2_port} Baud: {esp32h2_baud}"
                            }
                }
            )


            logger.info("Start Wait 3")
            print("Start Wait 3")
            time.sleep(3)
            logger.info("Finish Wait 3")
            print("Finish Wait 3")

        # IR Definition Handling
        if "write_ir_definition" in config:
            logger.info("Write IR Definition")
            print("Write IR Definition")
            command = config.get("write_ir_definition", "write_ir_definition_command")
            self.send_command(command + "\r\n")
            logger.info(f"Write IR Definition Command: {command}")
            print(f"Write IR Definition Command: {command}")
            time.sleep(5)  # Wait time for long command execution

        if "read_ir_definition" in config:
            logger.info("Read IR Definition")
            print("Read IR Definition")
            command = config.get("read_ir_definition", "read_ir_definition_command")
            self.send_command(command + "\r\n")
            logger.info(f"Read IR Definition Command: {command}")
            print(f"Read IR Definition Command: {command}")
            time.sleep(5)  # Wait time for long command execution
            # ir_definition = config.get("read_ir_definition", "read_ir_definition_data")
            # logger.info(f"IR Definition: {ir_definition}")
            ir_def = self.serialCom.get_ir_def()
            print(f"IR Definition: {ir_def}")
            
            ir_definition_data = config.get("read_ir_definition", "read_ir_definition_data")
            print(f"Test Script IR Definition Data: {ir_definition_data}")
            logger.info(f"Test Script IR Definition Data: {ir_definition_data}")
            
            if ir_def == ir_definition_data:
                logger.info("IR Definition: Pass")
                print("IR Definition: Pass")
                messagebox.showinfo("Information", "Reload IR Completed")
            else:
                logger.info("IR Definition: Failed")
                print("IR Definition: Failed")
                messagebox.showerror("Error", "Reload IR Failed")
                            
        logger.info("close_serial_port")
        self.datadog_logging(
                "info",
                {
                        "summary": "close_serial_port"
                }
            )
        print("close_serial_port")
        self.close_serial_port()
        
        self.initialize_serialCom(self.result_ir_def_label)
        
        return False


    # def process_reset_device(self):
    #     logger.info("Resetting device")
    #     self.send_command("FF:3;factoryRST\r\n")
    #     logger.info("Test Completed")
    #     self.reset_tasks()

    def fail_ui(self):
        logger.info("Resetting tasks")
        
        self.datadog_logging(
            "info",
            {
                    "summary": "Fail UI: Resetting tasks"
            }
        )
        
        self.result_flashing_fw_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_flashing_fw_h2_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_flashing_cert_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_factory_mode_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_read_device_mac.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.read_device_mac.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.result_write_serialnumber.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.read_device_sn.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.result_write_mtqr.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.read_device_mtqr.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.result_save_device_data_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.read_save_device_data_label.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.result_3_3v_test.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.range_value_3_3V_dmm.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.result_5v_test.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.range_value_5V_dmm.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.result_temp_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.range_temp_value.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.result_humid_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.range_humid_value.config(text="-", fg="black", font=("Helvetica", 10, "bold"))

        self.result_rgb_red_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_rgb_green_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_rgb_blue_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_rgb_off_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))

        self.result_button_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.dmm_3_3V_reader.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.dmm_5V_reader.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.atbeam_temp_value.config(text="AT °C", fg="black", font=("Helvetica", 10, "bold"))
        self.ext_temp_value.config(text="Ext °C", fg="black", font=("Helvetica", 10, "bold"))
        self.ext_raw_temp_value.config(text="Ext Raw °C", fg="black", font=("Helvetica", 10, "bold"))
        self.atbeam_humid_value.config(text="AT %", fg="black", font=("Helvetica", 10, "bold"))
        self.ext_humid_value.config(text="Ext %", fg="black", font=("Helvetica", 10, "bold"))
        self.ext_raw_humid_value.config(text="Ext Raw %", fg="black", font=("Helvetica", 10, "bold"))
        self.input_3_3V_dmm.delete(0, tk.END)
        self.input_5V_dmm.delete(0, tk.END)
        self.result_read_prod_name.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.read_prod_name.config(text="-", fg="black", font=("Helvetica", 10, "bold"))
        self.result_mac_address_s3_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_mac_address_h2_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_group2_factory_mode.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_group2_wifi_softap.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_group2_wifi_softap_rssi.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.range_group2_wifi_softap_rssi.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_group2_wifi_softap_ssid.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_group2_wifi_station.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_group2_wifi_station_rssi.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.range_group2_wifi_station_rssi.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_rgb_off_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_ir_def_label.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_ir_led1.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_ir_led2.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_ir_led3.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_ir_led4.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_ir_led5.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.cert_status_label.config(text=" ", fg="black", font=("Helvetica", 10, "bold"))
        self.result_short_header.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_factory_reset.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.result_h2_led_check.config(text="Failed", fg="red", font=("Helvetica", 10, "bold"))
        self.printer_qrpayload_data_label.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.printer_manualcode_data_label.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.printer_status_data_label.config(text="-", fg="black", font=("Helvetica", 10, "normal"))


    def reset_ui(self):
        global device_data
        global orderNum_label
        global macAddress_label
        global serialID_label
        global certID_label
        global secureCertPartition_label
        global commissionableDataPartition_label
        global qrCode_label
        global manualCode_label
        global discriminator_label
        global passcode_label
        global orderNum_data
        global macAddress_esp32s3_data
        global serialID_data
        global certID_data
        global secureCertPartition_data
        global commissionableDataPartition_data
        global qrCode_data
        global manualCode_data
        global discriminator_data
        global passcode_data

        logger.info("Resetting tasks")
        
        self.datadog_logging(
            "info",
            {
                    "summary": "Resetting tasks"
            }
        )
        
        self.clear_image_label()
        
        # self.result_ir_def_label.grid()
        
        device_data = ""

        orderNum_label = ""
        macAddress_label = ""
        serialID_label = ""
        certID_label = ""
        secureCertPartition_label = ""
        commissionableDataPartition_label = ""
        qrCode_label = ""
        manualCode_label = ""
        discriminator_label = ""
        passcode_label = ""

        orderNum_data = ""
        macAddress_esp32s3_data = ""
        serialID_data = ""
        certID_data = ""
        secureCertPartition_data = ""
        commissionableDataPartition_data = ""
        qrCode_data = ""
        manualCode_data = ""
        discriminator_data = ""
        passcode_data = ""

        self.status_fw_availability_label.config(fg="black")
        self.status_fw_availability_label.grid()
        self.status_espfuse_s3.config(fg="black")
        self.status_espfuse_s3.grid()
        self.read_mac_address_label.config(fg="black")
        self.read_mac_address_label.grid()
        self.status_flashing_fw.config(fg="black")
        self.status_flashing_fw.grid()
        self.status_flashing_cert.config(fg="black")
        self.status_flashing_cert.grid()
        self.status_factory_mode.config(fg="black")
        self.status_factory_mode.grid()
        self.status_read_device_mac.config(fg="black")
        self.status_read_device_mac.grid()
        self.status_read_device_firmware_version.config(fg="black")
        self.status_read_device_firmware_version.grid()
        self.status_read_prod_name.config(fg="black")
        self.status_read_prod_name.grid()
        self.status_write_device_sn.config(fg="black")
        self.status_write_device_sn.grid()
        self.status_read_device_matter_dac_vid.config(fg="black")
        self.status_read_device_matter_dac_vid.grid()
        self.status_read_device_matter_dac_pid.config(fg="black")
        self.status_read_device_matter_dac_pid.grid()
        self.status_read_device_matter_vid.config(fg="black")
        self.status_read_device_matter_vid.grid()
        self.status_read_device_matter_pid.config(fg="black")
        self.status_read_device_matter_pid.grid()
        self.status_read_device_matter_discriminator.config(fg="black")
        self.status_read_device_matter_discriminator.grid()
        self.status_write_device_mtqr.config(fg="black")
        self.status_write_device_mtqr.grid()
        self.result_ir_def.config(fg="black")
        self.result_ir_def.grid()
        self.status_save_device_data_label.config(fg="black")
        self.status_save_device_data_label.grid()
        self.status_5v_test.config(fg="black")
        self.status_5v_test.grid()
        self.status_3_3v_test.config(fg="black")
        self.status_3_3v_test.grid()
        self.status_atbeam_temp.config(fg="black")
        self.status_atbeam_temp.grid()
        self.status_atbeam_humidity.config(fg="black")
        self.status_atbeam_humidity.grid()
        self.status_test_irrx.config(fg="black")
        self.status_atbeam_humidity.grid()

        self.status_group2_factory_mode.config(fg="black")
        self.status_group2_factory_mode.grid()
        self.status_group2_wifi_softap_label.config(fg="black")
        self.status_group2_wifi_softap_label.grid()
        self.status_group2_wifi_station.config(fg="black")
        self.status_group2_wifi_station.grid()
        self.status_http_device_matter_discriminator.config(fg="black")
        self.status_http_device_matter_discriminator.grid()

        self.status_button_label.config(fg="black")
        self.status_button_label.grid()
        self.status_rgb_red_label.config(fg="black")
        self.status_rgb_red_label.grid()
        self.status_rgb_green_label.config(fg="black")
        self.status_rgb_green_label.grid()
        self.status_rgb_blue_label.config(fg="black")
        self.status_rgb_blue_label.grid()
        self.status_rgb_off_label.config(fg="black")
        self.status_rgb_off_label.grid()
        self.ir_led1_label.config(fg="black")
        self.ir_led1_label.grid()
        self.ir_led2_label.config(fg="black")
        self.ir_led2_label.grid()
        self.ir_led3_label.config(fg="black")
        self.ir_led3_label.grid()
        self.ir_led4_label.config(fg="black")
        self.ir_led4_label.grid()
        self.ir_led5_label.config(fg="black")
        self.ir_led5_label.grid()
        
        self.status_short_header.config(fg="black")
        self.status_short_header.grid()
        self.status_h2_led_check.config(fg="black")
        self.status_h2_led_check.grid()
        self.printer_label.config(fg="black")
        self.printer_label.grid()

        self.fw_availability_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_espfuse_s3.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))

        self.result_mac_address_s3_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_mac_address_h2_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        
        self.result_flashing_fw_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_flashing_fw_h2_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_flashing_cert_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_factory_mode_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_read_device_mac.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_mac.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_read_device_firmware_version.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_firmware_version.config(text="-", fg="black", font=("Helvetica", 10, "normal"))

        self.result_read_prod_name.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_prod_name.config(text="-", fg="black", font=("Helvetica", 10, "normal"))

        self.result_write_serialnumber.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_sn.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_read_device_matter_dac_vid.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_matter_dac_vid.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_read_device_matter_dac_pid.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_matter_dac_pid.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_read_device_matter_vid.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_matter_vid.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_read_device_matter_pid.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_matter_pid.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_read_device_matter_discriminator.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_matter_discriminator.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_write_mtqr.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_device_mtqr.config(text="-", fg="black", font=("Helvetica", 10, "normal"))

        self.result_ir_def_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))

        self.result_save_device_data_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_save_device_data_label.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_save_application_data_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.read_save_application_data_label.config(text="-", fg="black", font=("Helvetica", 10, "normal"))

        self.result_3_3v_test.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.range_value_3_3V_dmm.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_5v_test.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.range_value_5V_dmm.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.dmm_3_3V_reader.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.dmm_5V_reader.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.input_3_3V_dmm.delete(0, tk.END)
        self.input_5V_dmm.delete(0, tk.END)

        self.result_temp_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.range_temp_value.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_humid_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.range_humid_value.config(text="-", fg="black", font=("Helvetica", 10, "normal"))

        self.atbeam_temp_value.config(text="AT °C", fg="black", font=("Helvetica", 10, "normal"))
        self.ext_temp_value.config(text="Ext °C", fg="black", font=("Helvetica", 10, "normal"))
        self.ext_raw_temp_value.config(text="Ext Raw °C", fg="black", font=("Helvetica", 10, "normal"))
        self.atbeam_humid_value.config(text="AT %", fg="black", font=("Helvetica", 10, "normal"))
        self.ext_humid_value.config(text="Ext %", fg="black", font=("Helvetica", 10, "normal"))
        self.ext_raw_humid_value.config(text="Ext Raw %", fg="black", font=("Helvetica", 10, "normal"))
        
        
        self.result_test_irrx.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.test_irrx.config(text="-",fg="black", font=("Helvetica", 10, "normal"))

        self.result_group2_factory_mode.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_group2_wifi_softap.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_group2_wifi_softap_rssi.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.range_group2_wifi_softap_rssi.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_group2_wifi_softap_ssid.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_group2_wifi_station.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_group2_wifi_station_rssi.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.range_group2_wifi_station_rssi.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.result_http_device_matter_discriminator.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.http_device_matter_discriminator.config(text="-",fg="black", font=("Helvetica", 10, "normal"))

        self.result_button_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))

        self.result_rgb_red_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_rgb_green_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_rgb_blue_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_rgb_off_label.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_ir_led1.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_ir_led2.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_ir_led3.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_ir_led4.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_ir_led5.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))

        self.cert_status_label.config(text=" ", fg="black", font=("Helvetica", 10, "normal"))
        self.result_short_header.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.result_h2_led_check.config(text="Not Yet", fg="black", font=("Helvetica", 10, "normal"))
        self.printer_qrpayload_data_label.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.printer_manualcode_data_label.config(text="-", fg="black", font=("Helvetica", 10, "normal"))
        self.printer_status_data_label.config(text="-", fg="black", font=("Helvetica", 10, "normal"))

    def read_version_from_file(self, file_name):
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        try:
            with open(file_path, "r") as file:
                version = file.readline().strip()
                return version
        except FileNotFoundError:
            return "Version not found"

    def add_version_label(self, version):
        # Create a label for the version number
        version_label = tk.Label(self.scrollable_frame, text=f"Version: {version}")

        # Use a high row and column index to ensure it's at the bottom right
        version_label.grid(row=999, column=999, padx=10, pady=10, sticky=tk.SE)

        # Configure weights for the grid to ensure the label stays at the bottom right
        self.scrollable_frame.grid_rowconfigure(998, weight=1)
        self.scrollable_frame.grid_columnconfigure(998, weight=1)
        self.scrollable_frame.grid_rowconfigure(999, weight=1)
        self.scrollable_frame.grid_columnconfigure(999, weight=1)


    def on_exit(self):
        print('on_exit')
        self.root.destroy()
        logger.info("close_serial_port")
        self.datadog_logging(
            "info",
            {
                    "summary": "close_serial_port"
            }
        )
        print("close_serial_port")
        self.close_serial_port()
        print('on_exit-end')
        self.root.quit
        
    def datadog_logging(self, level, message):
        global formatted_date
        global formatted_time
        
        # Get the current date and time
        current_datetime = datetime.now()

        formatted_date = current_datetime.strftime("%Y-%m-%d")
        formatted_time = current_datetime.strftime("%H:%M:%S")
        
        # Get the MAC address of the Raspberry Pi
        rpi_mac_address = self.rpi_mac_address('wlan0')
                
        if level in ["info", "error"]:
            log_function = getattr(logger, level)
            log_function(json.dumps({
                "rpi_mac_address": rpi_mac_address,
                "date": formatted_date,
                "time": formatted_time,
                "filename": logs_file_name,
                "order_number": orderNum_data,
                "mac_address": macAddress_esp32s3_data,
                "serial_number": serialID_data,
                "factory_app_version": factory_app_version,
                "message": message
            }))
            
    def rpi_mac_address(self, interface='wlan0'):
        try:
            result = subprocess.check_output(["cat", f"/sys/class/net/{interface}/address"])
            mac_address = result.decode('utf-8').strip()
            return mac_address
        except subprocess.CalledProcessError:
            print(f"Error: Could not retrieve MAC address for interface {interface}")
            return None
            

# if __name__ == "__main__":

#     #Check if logs folder exist on boot
#     if (os.path.isdir(logs_dir) == False):
#         os.chdir(script_dir)
#         os.mkdir(logs_dir_name)

#     # Delete "sensor.txt" file during boot up
#     # sensor_file = "sensor.txt"
#     sensor_file = f"{sensor_txt_fullpath}"
#     if os.path.exists(sensor_file):
#         os.remove(sensor_file)

#     root = tk.Tk()
#     app = SerialCommunicationApp(root)

#     root.protocol("WM_DELETE_WINDOW", app.on_exit)
#     root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Serial Communication App.")
    parser.add_argument("--debug", action="store_true", help="Run the app in debug (windowed) mode.")
    args = parser.parse_args()

    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir_name = "logs"
    logs_dir = os.path.join(script_dir, logs_dir_name)
    sensor_txt_fullpath = os.path.join(script_dir, "sensor.txt")

    # Check if logs folder exists on boot
    if not os.path.isdir(logs_dir):
        os.chdir(script_dir)
        os.mkdir(logs_dir_name)

    # Delete "sensor.txt" file during boot up
    if os.path.exists(sensor_txt_fullpath):
        os.remove(sensor_txt_fullpath)

    # Initialize the app
    root = tk.Tk()
    app = SerialCommunicationApp(root, debug_mode=args.debug)
    root.protocol("WM_DELETE_WINDOW", app.on_exit)
    root.mainloop()