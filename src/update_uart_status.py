#!/bin/python3
import RPi.GPIO as GPIO
import os
import time
invalid_list=[24,23,22] #0,2,3

def init():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(invalid_list,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

def update_status():
    try:
        os.system(f"echo '{GPIO.input(24)}'|sudo tee /dev/piUART/status/ttyAMA0")
        os.system(f"echo '{GPIO.input(23)}'|sudo tee /dev/piUART/status/ttyAMA2")
        os.system(f"echo '{GPIO.input(22)}'|sudo tee /dev/piUART/status/ttyAMA3")
    except:
        print("Error, did you run this as root?")


if __name__ == '__main__':
    init()
    while 1:
        update_status()
        time.sleep(5)