import tkinter as tk
import configparser
import os

class SettingApp:
    def __init__(self, master):
        self.master = master
        master.title("Address Configuration")
        master.geometry("500x300")  # Set initial window size

        self.labels = ["Bootloader", "Partition_Table", "OTA_Data_Initial", "Firmware", "Matter_Cert", "AWS_Cert"]

        self.entries = {}
        for idx, label in enumerate(self.labels):
            tk.Label(master, text=label + " Address", font=("Arial", 12)).grid(row=idx+1, column=0, padx=10, pady=5, sticky="w")
            self.entries[label] = tk.Entry(master, font=("Arial", 12), width=30)
            self.entries[label].grid(row=idx+1, column=1, padx=10, pady=5, sticky="w")

        self.save_button = tk.Button(master, text="Save", command=self.save_settings, font=("Arial", 12))
        self.save_button.grid(row=len(self.labels)+1, column=0, columnspan=2, pady=10)

        # Label to display save status
        self.status_label = tk.Label(master, text="", font=("Arial", 10), fg="green")
        self.status_label.grid(row=len(self.labels)+2, column=0, columnspan=2, pady=5)

    def save_settings(self):
        settings = {}
        for label, entry in self.entries.items():
            settings[label] = entry.get()

        config = configparser.ConfigParser()

        if os.path.exists('config.ini'):
            config.read('config.ini')
        else:
            config['Settings'] = {}

        for key, value in settings.items():
            config['Settings'][key] = value

        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        
        self.status_label.config(text="Settings saved successfully.", fg="green")