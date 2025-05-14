import os
from components.dmmReader.dmmReader import DeviceSelectionApp

class Multimeter:
    def get_hidraw_devices(self):
        hidraw_devices = [device for device in os.listdir('/dev') if device.startswith('hidraw')]
        return hidraw_devices

    def read_multimeter_voltage(self):
        return 5.1    # Replace with actual voltage reading

    # Function to determine if the voltage reading is within the expected range for 3.3V
    def is_3_3_voltage(self, voltage):
        return 3.0 <= voltage <= 3.6

    # Function to determine if the voltage reading is within the expected range for 5V
    def is_5_voltage(self, voltage):
        return 4.8 <= voltage <= 5.2

    def main(self):
        voltage = self.read_multimeter_voltage()
        
        if self.is_3_3_voltage(voltage):
            print("Voltage reading from 3.3V multimeter:", voltage)
        elif self.is_5_voltage(voltage):
            print("Voltage reading from 5V multimeter:", voltage)
        else:
            print("Invalid voltage reading:", voltage)

# Create an instance of the DeviceSelectionApp class and call the main method
if __name__ == "__main__":
    app = DeviceSelectionApp()
    app.main()
