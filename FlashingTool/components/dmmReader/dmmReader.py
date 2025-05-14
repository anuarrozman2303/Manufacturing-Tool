import tkinter as tk
from tkinter import messagebox, ttk
import hid
from components.dmmReader.ut61eplus import UT61EPLUS
import logging
import os
# import multiprocessing

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(__file__)

dmmReader_output_file = str(script_dir) + "/../../dmm_output.txt" 

class DeviceSelectionApp:
    def __init__(self, parent_frame, status_label1, status_label2):
        self.parent_frame = parent_frame
        self.devices = []
        self.create_widgets()
        # self.refresh_devices()
        self.status_label1 = status_label1
        self.status_label2 = status_label2

    def create_widgets(self):
        self.device_label = tk.Label(self.parent_frame, text="Multimeter/万用表:", state=tk.NORMAL)
        self.device_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        self.device_buttons_frame = tk.Frame(self.parent_frame)
        self.device_buttons_frame.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W)

        self.refresh_button = tk.Button(self.parent_frame, text="Refresh/刷新", command=self.refresh_devices, state=tk.DISABLED)
        self.refresh_button.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.refresh_button.grid_forget()

    def refresh_devices(self):

        multimeters = []
        try:
            multimeters = hid.enumerate(UT61EPLUS.CP2110_VID, UT61EPLUS.CP2110_PID)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            logger.error(f"Error refreshing devices: {e}")
        else:
            nof_multimeter = len(multimeters)
            print("")
            print("")
            print(f"Found {nof_multimeter} CP2110 based multimeter")
            print("")
            print("")
            for i in range(len(multimeters)):
                self.devices.append(multimeters[i])
            # print(devicelist)

        multimeters = []
        try:
            multimeters = hid.enumerate(UT61EPLUS.QinHeng_VID, UT61EPLUS.QinHeng_PID)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            logger.error(f"Error refreshing devices: {e}")
        else:
            nof_multimeter = len(multimeters)
            print("")
            print("")
            print(f"Found {nof_multimeter} QinHeng based multimeter")
            print("")
            print("")
            for i in range(len(multimeters)):
                self.devices.append(multimeters[i])

        print("")
        print("")
        print("Connected Multimeter Info Array")
        print("")
        print("")
        print(self.devices)
        print("")
        print("")
        
        self.update_device_buttons()

        # for i in range(len(self.devices)):
        #     self.select_device(i)

    def update_device_buttons(self):
        # Clear existing buttons
        for widget in self.device_buttons_frame.winfo_children():
            widget.destroy()

        # Create buttons for each device
        for i, device in enumerate(self.devices):
            button = tk.Button(self.device_buttons_frame, text=f"Multimeter/万用表 {i}", command=lambda idx=i: self.select_device(idx), state=tk.DISABLED if not self.devices else tk.NORMAL)
            button.grid(row=0, column=i, padx=5, pady=5, sticky=tk.W)

    def insert_3_3V_dmm2entry(self, volt):
        self.status_label1.delete(0, tk.END)
        self.status_label1.insert(0, volt)

    def insert_5V_dmm2entry(self, volt):
        self.status_label2.delete(0, tk.END)
        self.status_label2.insert(0, volt)
        
    def select_device(self, device_number):
        try:
            if device_number < len(self.devices):
                # print(f"Selected device: {self.devices[device_number]}")
                logger.info(f"Selected device: {self.devices[device_number]}")
                print(f"Selected device: {self.devices[device_number]}")
                logger.info(f"Device Number: {device_number}")
                print(f"Device Number: {device_number}")
                self.read_multimeter(device_number)
            else:
                # messagebox.showerror("Error", "Selected device number is out of range.")
                logger.error("Selected device number is out of range.")
                print("Selected device number is out of range.")
        except Exception as e:
            # messagebox.showerror("Error", str(e))
            logger.error(f"Error selecting device: {e}")
            print(f"Error selecting device: {e}")

    def read_multimeter(self, device_number):
        try:
            dev = UT61EPLUS(device_number)  # Pass the selected device number to UT61EPLUS
            dmm = dev
            dmm.writeMeasurementToFile(str(dmmReader_output_file))
            multimeter_name = dmm.getName()
            print(f"Multimeter Name: {multimeter_name}")
            dmm.sendCommand('lamp')

            measurement = dmm.takeMeasurement()
            if hasattr(measurement, 'display'):
                display_value = float(measurement.display)
                # messagebox.showinfo("Measurement", f"Measurement: {display_value}")
                logger.info(f"Measurement: {display_value}")
                print(f"Measurement: {display_value}")
                # self.check_voltage(display_value)
                if device_number:
                    self.insert_3_3V_dmm2entry(display_value)
                else:
                    self.insert_5V_dmm2entry(display_value)
            else:
                # messagebox.showerror("Measurement Error", "Failed to extract display value from measurement.")
                logger.error("Failed to extract display value from measurement.")
                print("Failed to extract display value from measurement.")
        except Exception as e:
            # messagebox.showerror("Error", str(e))
            logger.error(f"Error reading multimeter: {e}")
            print(f"Error reading multimeter: {e}")

    def check_voltage(self, voltage):
        if self.is_3_3_voltage(voltage):
            # messagebox.showinfo("Voltage Reading", f"Voltage reading from 3.3V multimeter: {voltage}")
            logger.info(f"Voltage reading from 3.3V multimeter: {voltage}")
            print(f"Voltage reading from 3.3V multimeter: {voltage}")
            self.status_label1.delete(0, tk.END)
            self.status_label1.insert(0, voltage)
        elif self.is_5_voltage(voltage):
            # messagebox.showinfo("Voltage Reading", f"Voltage reading from 5V multimeter: {voltage}")
            logger.info(f"Voltage reading from 5V multimeter: {voltage}")
            print(f"Voltage reading from 5V multimeter: {voltage}")
            self.status_label2.delete(0, tk.END)
            self.status_label2.insert(0, voltage)
        else:
            # messagebox.showinfo("Voltage Reading", f"Invalid voltage reading: {voltage}")
            logger.info(f"Invalid voltage reading: {voltage}")
            print(f"Invalid voltage reading: {voltage}")
            # self.status_label1.delete(0, tk.END)
            # self.status_label2.delete(0, tk.END)
            # self.status_label1.insert(0, voltage)
            # self.status_label2.insert(0, voltage)
            
    def is_3_3_voltage(self, voltage):
        # Later change to 3V - 4V
        if 1.00 < voltage < 5.00:
            # self.status_label1.config(text=f"Success {voltage}")
            return True
        else:
            return False

    def is_5_voltage(self, voltage):
        # Later change to 4.9V - 5.1V
        if 3.00 < voltage <= 7.00:
            # self.status_label2.config(text=f"Success: {voltage}")
            return True
        else:
            return False
