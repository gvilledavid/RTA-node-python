import os,sys
import threading
import serial
import threading
import time
import queue
import importlib

#local includes
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger


def get_uart_data(tty, brate, tout, cmd, par=serial.PARITY_NONE,rts_cts=0):
    with serial.Serial(tty, brate, timeout=tout,
            parity=par, rtscts=rts_cts) as ser:
        ser.flush()
        ser.write(cmd)
        line = ser.readline()
        ser.close()
        return line
    
class UARTLeafManager:
    #class var
    parsers={}
    def __init__(self, interface, parentUID, logger=None):
        self.interface=interface
        self.parser=None
        self.baud=0
        self.UID=f"{parentUID}:{interface}"
        
        if not logger:
            self.logger = RotatingLogger(f"UARTLeafManager-{interface}.log")
        else:
            self.logger = logger
        self.runner=threading.Thread(target=self.loop_runner, args=())
        self.running=False
        self.stopped=True
        self.rxQueue=queue.PriorityQueue(maxsize=1000)
        self.txQueue=queue.PriorityQueue(maxsize=1000)
        
    def scan_baud(self):
        pass
    def process_commands(self,brate):
        #swap baud rate(brate): self.parser.serial_info["brate"]=brate
        #datamode(mode): self.parser.datamode(mode)
        #change send frequency: self.parser.set_frequency()
        #change pulse send freq
        #swap device: self.parser.shutdown, del self.parser, self.parser= new parser, go through the init process
        #immedate pulse: send pulse now
        #update parsers: get a file, hash, etc and update a parser
        #req_id: hand out req_ids for command/responses to work
        #start/stop commands?
        pass
    def loop_start(self):
        #need to add flags here
        self.running=True
        self.stopped=False
        self.runner.start()
        
    def loop_runner(self):
        #add flags, exception handling
        while self.running:
            while not self.parser.scan_connection():
                self.find_parser()
        self.stopped=True
    def is_alive(self):
        self.runner.join(timeout=0)
        #should we check the flags?
        return self.runner.is_alive()
    def pulse(self):
        self.UID
        self.parser.DID
		self.parser.vent_type
		self.parser.baud #last known good baud
		self.parser.protocol
		#use self.parser.status and your own knowledge of hardware to define status here
		timestamp=str(int(time.time()*1000)), 

  
  
  
    def loop_stop(self):
        self.running=False
        ct=0
        tMAX=10
        while self.is_alive():
            ct+=1
            time.sleep(.1)
            if ct>tMAX:
                break
    def enumerate_parsers(self):
        #iterate through ./parsers and add them to a list, also import them all
    
    def update_parser(self):
        pass
    def reload_parser(self,sys_name):
        #"parsers.parser1.parser1"
        #first check if you are using this 
        importlib.reload(sys.modules[sys_name])