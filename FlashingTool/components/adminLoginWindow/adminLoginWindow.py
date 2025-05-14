import tkinter as tk
from tkinter import messagebox
from cryptography.fernet import Fernet
import os

class AdminLoginApp:
    def __init__(self, master, caller):
        self.master = master
        self.caller = caller
        master.title("Admin Login")
        master.geometry("350x120")

        self.label = tk.Label(master, text="Enter password:", font=("Arial", 12))
        self.label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.password_entry = tk.Entry(master, show="*", font=("Arial", 12))  # Hide entered text
        self.password_entry.grid(row=0, column=1, padx=10, pady=10)

        self.login_button = tk.Button(master, text="Login", command=self.check_password, font=("Arial", 12))
        self.login_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.result = False

        self.key = self.load_key()

    # Loading the key from a file or generating a new key
    # Im using Fernet symmetric encryption to encrypt the password
    def load_key(self):
        key_file = "secret.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as keyfile:
                key = keyfile.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as keyfile:
                keyfile.write(key)
        return key

    # Encrypting the password using the key
    def encrypt_password(self, password):
        fernet = Fernet(self.key)
        encrypted_password = fernet.encrypt(password.encode())
        return encrypted_password

    # Saving the encrypted password to a file
    def save_password(self, encrypted_password):
        with open("password.txt", "wb") as password_file:
            password_file.write(encrypted_password)

    # Checking the password entered by the user
    def check_password(self):
        password = self.password_entry.get()
        # Replace 'admin' with the actual password
        if password == "admin":
            self.result = True
            print("Login successful!")
            encrypted_password = self.encrypt_password(password)
            self.save_password(encrypted_password)
            self.master.destroy()
        else:
            messagebox.showerror("Error", "Invalid password!")

            self.caller.disable_frame(self.caller.text_frame)
            self.caller.text_frame.grid_forget()
            
            self.caller.disable_frame(self.caller.servo_frame)
            self.caller.servo_frame.grid_forget()
            
            #self.caller.disable_frame(self.caller.dmm_frame)
            #self.caller.dmm_frame.grid_forget()
                        
            #self.caller.disable_frame(self.serial_baud_frame)
            #self.caller.serial_baud_frame.grid_forget()
            self.caller.flash_button.grid_forget()
            self.caller.cert_flash_button.grid_forget()
            #self.caller.port_label1.grid_forget()
            self.caller.flash_button.grid_forget()
            self.caller.baud_dropdown.grid_forget()
            self.caller.baud_dropdown1.grid_forget()
            self.caller.open_port_button.grid_forget()
            self.caller.close_port_button.grid_forget()
            self.caller.read_device_mac_button.grid_forget()
            self.caller.write_device_serialnumber_button.grid_forget()
            self.caller.write_device_mtqr_button.grid_forget()
            self.caller.read_atbeam_temp_button.grid_forget()
            self.caller.read_atbeam_humid_button.grid_forget()
            self.caller.exit_button.grid_forget()
            self.caller.baud_label1.grid_forget()
            self.caller.baud_label.grid_forget()

