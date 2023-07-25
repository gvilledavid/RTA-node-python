import RPi.GPIO as GPIO
import time
import sys
chan=8
duty=100
freq=20
def faninit(fchan):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.gpio_function(fchan)
        GPIO.setup(chan,GPIO.OUT)
def fan(fduty,ffreq,fchan):
        for i in range(5*ffreq):
                GPIO.output(fchan, GPIO.HIGH)
                time.sleep(fduty/(100*ffreq))
                GPIO.output(fchan, GPIO.LOW)
                time.sleep((100-fduty)/(100*ffreq))
def main(args):
        if(len(argv)==3):
                faninit(argv[2])
                fan(argv[0],argv[1],argv[2])
        else:
                faninit(chan)
                fan(duty,freq,chan)
        GPIO.cleanup()

if __name__ == '__main__'
        main(sys.argv)