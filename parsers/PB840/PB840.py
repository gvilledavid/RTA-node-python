import os,sys,time
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from  parsers.parser import parser
 
class PB840(parser):
    def loop_main():
        self.send_message()
        self.parse
    def parse()