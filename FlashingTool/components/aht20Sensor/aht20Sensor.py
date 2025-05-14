from . import AHT20  # Assuming AHT20 is the name of the module where AHT20 class is defined
import logging

logger = logging.getLogger(__name__)

class SensorLogger:
    def __init__(self):
        # Instantiate the AHT20 class from the module
        self.aht20 = AHT20.AHT20()

    def read_temp_sensor(self):
        #  data = self.aht20.get_temperature()
         data_crc8 = "{:10.2f}".format(self.aht20.get_temperature()) + " °C"
         return data_crc8

    def read_humid_sensor(self):
        #  data = self.aht20.get_humidity()
         data_crc8 = "{:10.2f}".format(self.aht20.get_humidity()) + " %RH"
         return data_crc8
