import tkinter as tk
from tkinter import ttk
from configparser import ConfigParser
import os
import logging

logger = logging.getLogger(__name__)

class ManualTestApp:
    def __init__(self, root, send_command):
        self.root = root
        self.send_command = send_command

    def open_manual_test_window(self):
        manual_test_window = tk.Toplevel(self.root)
        manual_test_window.title("Manual Test")
        manual_test_window.minsize(400, 300)

        manual_test_frame = ttk.Frame(manual_test_window)
        manual_test_frame.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        # Search for manual_test.ini starting from the root directory
        config_path = self.find_manual_test_ini("/")
        if config_path:
            self.create_buttons_from_config(self.load_config(config_path), manual_test_frame)
        else:
            print("manual_test.ini not found.")    
    
    def find_manual_test_ini(self, start_dir):
        for dirpath, dirnames, filenames in os.walk(start_dir):
            if "manual_test.ini" in filenames:
                return os.path.join(dirpath, "manual_test.ini")
        return None
    
    def create_buttons_from_config(self, config, parent):
        sections = config.sections()
        buttons = {}
        for section in sections:
            section_frame = tk.LabelFrame(parent, text=section)
            section_frame.pack(padx=10, pady=5, fill="both", expand=True)

            for key, value in config.items(section):
                # Append \r\n to the value to ensure correct line endings
                value_with_line_endings = value + "\r\n"
                button = tk.Button(section_frame, text=key, command=lambda v=value_with_line_endings: self.send_command(v))
                button.pack(side=tk.LEFT, padx=5, pady=5)
                buttons[key] = button
        return buttons
    
    def load_config(self, filename):
        config = ConfigParser()
        config.read(filename)
        return config