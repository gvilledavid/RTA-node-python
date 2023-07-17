import RPi.GPIO as GPIO
import sys
import time
import os
import subprocess
# UART00   tx rx cts rts 
# UART02                 tx rx cts rts
# UART03                              tx rx cts rts
uart_list=[14,15, 16, 17, 4, 5, 6, 7,  8, 9, 10, 11] #BCM 
forceON=27
invalid_list=[24,23,22] #0,2,3
#echo '1'|sudo tee AMA3

def uart_init():
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(forceON,GPIO.OUT)
	GPIO.output(forceON, GPIO.LOW)#high will disable auto powerdown
	GPIO.setup(invalid_list,GPIO.IN)
	GPIO.setup(uart_list,GPIO.SERIAL)
	
def update_status:
	ret=subprocess.check_output("echo '1'|sudo tee AMA3",shell=True)
	
GPIO.input(24)	=1 when connected, 0 when not

if __name__ == '__main__' 
	loop
		check /dev/piUART/forceON 
			GPIO.output(fchan, GPIO.HIGH) or low depending on status
			udpate with echo "0"|sudo tee forceON
		check invlaid_list and update /dev/piUART/status/. 
		

https://stackoverflow.com/questions/182197/how-do-i-watch-a-file-for-changes