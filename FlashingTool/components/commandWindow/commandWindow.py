# components/settingsPage/settingsPage.py

import tkinter as tk
from configparser import ConfigParser

class CommandWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Settings")
        self.config = ConfigParser()
        self.config.read('sendCommand.ini')

        self.create_widgets()
        self.load_settings()

    def create_widgets(self):
        self.serial_number_label = tk.Label(self.master, text="Serial Number:")
        self.serial_number_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.serial_number_entry = tk.Entry(self.master)
        self.serial_number_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.device_id_label = tk.Label(self.master, text="Device ID:")
        self.device_id_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.device_id_entry = tk.Entry(self.master)
        self.device_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.save_button = tk.Button(self.master, text="Save", command=self.save_settings)
        self.save_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

    def load_settings(self):
        if 'SETTINGS' in self.config:
            self.serial_number_entry.insert(0, self.config['SETTINGS'].get('SerialNumber', ''))
            self.device_id_entry.insert(0, self.config['SETTINGS'].get('DeviceID', ''))

    def save_settings(self):
        if 'SETTINGS' not in self.config:
            self.config.add_section('SETTINGS')
        
        self.config['SETTINGS']['SerialNumber'] = self.serial_number_entry.get()
        self.config['SETTINGS']['DeviceID'] = self.device_id_entry.get()

        with open('sendCommand.ini', 'w') as configfile:
            self.config.write(configfile)

        self.master.destroy()
