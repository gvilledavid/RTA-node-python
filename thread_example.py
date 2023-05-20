from queue import Queue
from threading import Thread
from time import sleep
class leaf_runner:
    def __init__(self, sleep_time,name):
        self.command_queue=Queue()
        self.name=name
        self.output_queue=Queue()
        self.runner=Thread(target=self.run(),args=())
        self.sleep_time=sleep_time
        self.data=0
    def run(self):
        while True:
            print(f"Thread {self.name} running.")
            self.output_queue.put(data)
            data+=1
            while(self.command_queue.qsize()):
                print(f"Recieved {self.command_queue.get()}")
            print(f"Thread {self.name} sleeping.")
            sleep(self.sleep_time)

if __name__=="__main__":
    leaf1=leaf_runner(2,"fast")
    leaf2=leaf_runner(10,"slow")
    leaf1.runner.start()
    leaf2.runner.start()
    while input().lower()!="exit\n":
        pass
