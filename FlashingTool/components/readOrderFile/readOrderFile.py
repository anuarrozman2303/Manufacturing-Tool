# components/readOrderFile.py
from tkinter import messagebox

def parse_order_file(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
    
        orders = []
        for line in lines:
            order_data = {}
            pairs = line.split(', ')
            for pair in pairs:
                key, value = pair.split(': ', 1)
                order_data[key] = value
            orders.append(order_data)

        return orders
    
    except Exception as e:
        print("Error at readOrderFile.py!")
        print(f"File is missing! - ' {file_path} ' ")
        messagebox.showerror("Error", f" ' {file_path} ' - Missing")

        return ""
    
