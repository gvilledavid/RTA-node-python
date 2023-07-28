import os
import threading
import serial

def get_uart_data(tty, brate, tout, cmd, par=serial.PARITY_NONE,rts_cts=0):
    with serial.Serial(tty, brate, timeout=tout,
            parity=par, rtscts=rts_cts) as ser:
        ser.flush()
        ser.write(cmd)
        line = ser.readline()
        ser.close()
        return line
    
class UARTLeafManager:
    def __init__(self, interface, parentUID):
        self.interface=interface
        self.parser=None
        self.baud=0
        
    def scan_baud(self):
        
    