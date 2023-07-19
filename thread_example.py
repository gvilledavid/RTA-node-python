from queue import Queue
from threading import Thread
from time import sleep


class leaf_runner:
    def __init__(self, sleep_time, name):
        print("parent constructor")
        self.command_queue = Queue()
        self.name = name
        self.output_queue = Queue()
        self.sleep_time = sleep_time
        self.data = 0
        self.runner = Thread(target=self.run, args=())
        print("ending parent constructor")

    def run(self):
        while True:
            print(f"Thread {self.name} running.")
            self.output_queue.put(self.data)
            self.data += 1
            while self.command_queue.qsize():
                print(f" {self.name}  recieved {self.command_queue.get()}")
            print(f" {self.name} thread {self.name} sleeping.")
            sleep(self.sleep_time)


class test(leaf_runner):
    def __init__(self):
        print("print inheritor constructor")


if __name__ == "__main__":
    test()

    leaf1 = leaf_runner(2, "fast")
    leaf2 = leaf_runner(10, "slow")
    leaf2.runner.start()
    leaf1.runner.start()
    data = 0
    while True:
        leaf1.command_queue.put(data)
        leaf2.command_queue.put(data)
        data += 1
        if data >= 20:
            leaf1.runner.join()
            leaf2.runner.join()
            break
        sleep(5)
