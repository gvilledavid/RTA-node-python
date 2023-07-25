#!/bin/python3
import RPi.GPIO as GPIO
import subprocess
import time
invalid_list=[24,23,22] #0,2,3

def init():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(invalid_list,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
if __name__ == '__main__':
    init()
    ttyAMAs={}#devices we are managing
    ttyAMAs["ttyAMA0"]=GPIO.input(24)
    ttyAMAs["ttyAMA2"]=GPIO.input(23)
    ttyAMAs["ttyAMA3"]=GPIO.input(22)
    ttyAMAs["ttyAMA1"]="?"
    ttyAMAs["ttyAMA4"]="?"
    ttyUSBs={}
    try:
        usbs=str(subprocess.check_output("ls /dev/piUART/status/ |grep ttyUSB*",shell=True))[2:-3].split("\\n")
        for dev in usbs:
            ttyUSBs[dev]=0
    except:
        pass#no usbs managed 
        
    while 1:
        try:
            x=str(subprocess.check_output("ls /dev/ |grep ttyUSB*",shell=True))[2:-3].split("\\n")
        except:
            #no usbs detected
            for usb in ttyUSBs:
                ttyUSBs[usb]=0
        else:
            
            read ls /dev/piUART/status 
            
            
            
            x=subprocess.check_output(f"echo '{GPIO.input(24)}'|sudo tee /dev/piUART/status/ttyAMA0",shell=True)
            x=subprocess.check_output(f"echo '{GPIO.input(23)}'|sudo tee /dev/piUART/status/ttyAMA2",shell=True)
            x=subprocess.check_output(f"echo '{GPIO.input(22)}'|sudo tee /dev/piUART/status/ttyAMA3",shell=True)
        try:
            usbs=str(subprocess.check_output("ls /dev/ |grep ttyUSB*",shell=True))[2:-3].split("\\n")
        except:
            pass#no usb device status monitored
            x=str(subprocess.check_output("ls /dev/ |grep ttyUSB*",shell=True))[2:-3].split("\\n")
            
    except:
        print("Error, did you run this as root?")

        
        
        
        
        
        
        time.sleep(5)