#!/bin/python3

import RPi.GPIO as GPIO

invalid=[24,25,26,27]
def init():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(invalid, GPIO.IN)
def stat():
    ret=[]
    for x in invalid:
            ret.append(f"AMAtty{x-23}:{GPIO.input(x)}")
    #print(ret)
    return ret
if __name__=="__main__":
    init()
    print(stat())