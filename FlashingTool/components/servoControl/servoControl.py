import RPi.GPIO as GPIO

class ServoController:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(12, GPIO.OUT)
        self.servo = GPIO.PWM(12, 50) # GPIO 12 for PWM with 50Hz
        self.servo.start(0)

    def set_angle(self, angle):
        angle2duty = 2 + ((angle / 180) * 10)
        self.servo.ChangeDutyCycle(angle2duty)

    def stop(self):
        self.servo.stop()
        GPIO.cleanup()
