import RPi.GPIO as GPIO
import time

class RebootPinS3:
    
    def __init__(self, gpio_pin=18):
        # Define the GPIO pin
        self.gpio_pin = gpio_pin

        # Set up the GPIO pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_pin, GPIO.OUT)

    # Function to set the GPIO pin high
    def set_pin_high(self):
        GPIO.output(self.gpio_pin, GPIO.HIGH)
        print("GPIO pin set to HIGH")

    # Function to set the GPIO pin low
    def set_pin_low(self):
        GPIO.output(self.gpio_pin, GPIO.LOW)
        print("GPIO pin set to LOW")

    # Function to reboot ESP32-S3
    def reboot_esp32(self):
        self.set_pin_high()
        time.sleep(1)  # Wait for 100 ms
        self.set_pin_low()
        time.sleep(1)  # Wait for 100 ms
        self.set_pin_high()
        # time.sleep(1)  # Wait for 100 ms

    # Clean up GPIO settings
    def cleanup(self):
        GPIO.cleanup()


if __name__ == "__main__":
    reboot_pin = RebootPinS3()
    reboot_pin.reboot_esp32()
    reboot_pin.cleanup()
# Example usage
# reboot_pin = RebootPinS3()
# reboot_pin.reboot_esp32()
# reboot_pin.cleanup()
