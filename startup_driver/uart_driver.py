import RPi.GPIO as GPIO
import sys
import time
import os
import subprocess

# UART02   tx rx cts rts
# UART03                 tx rx cts rts
# UART04                               tx rx cts rts
# UART05                                             tx rx
# UART00                                                   tx rx cts rts
uart_list=[0 ,1, 2,  3,  4, 5, 6,  7,  8, 9, 10, 11, 12,13,14,15,16, 17 ] #BCM
EN=20 #low to enable chips
force_on=18 #low to enable autopower down
force_off=19 #high to enable drivers
invalid=[24,25,26,27] #goes high when valid rs232 signals detected by reciever



if __name__ == '__main__':
    #enable max3223
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup( [ EN, force_on, force_off ],GPIO.OUT)
    GPIO.output(EN, GPIO.LOW)
    GPIO.output(force_on, GPIO.HIGH)#high will disable auto powerdown
    GPIO.output(force_off,GPIO.HIGH)
    GPIO.setup(invalid,GPIO.IN)
    while True:
        print("\n"*50)
        print("Port 1 Port 2 Port 3 Port 4")
        print(f"  {'   |  '.join(map(str,[GPIO.input(x) for x in invalid]))}")
        time.sleep(2)



import sys, os, subprocess
interfaces=[]
for x in str(subprocess.check_output("sudo dmesg |grep -e ttyAMA[1-4]",shell=True))[2:-3].split("\\n"):
    try:
        index=x.find("tty")
        tty=x[index:index+8].strip(" ")
        interfaces.append(tty)
    except:
        print("nothing found")

print(interfaces)

sudo dmesg |grep -e ttyAMA[1-4]
