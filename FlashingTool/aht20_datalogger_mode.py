import os
import time

from datetime import datetime
from components.aht20Sensor.aht20Sensor import SensorLogger

script_dir = os.path.dirname(__file__)

formatted_date = ""
formatted_time = ""

logs_file_name = "aht20_data"
logs_file_extension = ".log"
logs_dir_name = "aht20"
logs_dir = str(script_dir) + "/" + str(logs_dir_name)
log_file_name = ""

def initialize_logging():
        global formatted_date
        global formatted_time
        global logs_dir
        global log_file_name
        
        # Get the current date and time
        current_datetime = datetime.now()

        formatted_date = current_datetime.strftime("%Y%m%d")
        formatted_time = current_datetime.strftime("%H%M%S")

        # Configure logging
        log_file_name = logs_dir + "/" + str(formatted_date) + '_' + str(formatted_time) + '_' + logs_file_name + logs_file_extension
        print(str(log_file_name))
        
        return False

def write_logging(data_to_append):
    global log_file_name

    try:
        with open(log_file_name, "a") as file:
            file.write(str(data_to_append))
        print(f"Data appended to {log_file_name}")
    except IOError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":

    #Check if logs folder exist on boot
    if (os.path.isdir(logs_dir) == False):
        os.chdir(script_dir)
        os.mkdir(logs_dir_name)

    initialize_logging()

    while True:
        # Get the current date and time
        current_datetime = datetime.now()

        datestring = current_datetime.strftime("%Y/%m/%d")
        timestring = current_datetime.strftime("%H:%M:%S")

        temperature_reading = SensorLogger().read_temp_sensor()
        humidity_reading = SensorLogger().read_humid_sensor()

        log_data_string = str(datestring) + ' , ' + str(timestring) + ' , ' + str(temperature_reading) + ' , ' + str(humidity_reading) + '\n'
        write_logging(log_data_string)
        print(str(log_data_string))

        time.sleep(30)
