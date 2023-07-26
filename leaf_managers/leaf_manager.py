import os
import threading
import serial

def get_uart_data(tty, brate, tout, cmd):
    with serial.Serial(tty, brate, timeout=tout,
            parity=serial.PARITY_NONE, rtscts=0) as ser:
        ser.flush()
        ser.write(cmd)
        line = ser.readline()
        # print( line )
        ser.close()
        return line
    
class UARTLeafManager:
    def __init__(self, interface, parentUID):
        self.interface=interface
        self.parser=None
        self.baud=0
        
    def scan_baud(self):
        
    