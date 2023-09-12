import os, sys
import threading
import time
import queue
import importlib
import serial
import json

# local includes
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger
from parsers.parser import example_parser, default_parser
from tools.MQTT import Message
from parsers.parser import import_parsers


class UARTLeafManager:
    # class var
    parsers = {}

    def __init__(self, interface, parentUID, logger=None):
        self.interface = interface
        self.baud = 0
        self.parent = parentUID
        self.UID = f"{parentUID}:{interface}"
        self.command_topic = f"Commands/{self.UID}"
        self.response_topic = f"Devices/responses/{self.UID}"
        self.pulse_topic = f"Pulse/leafs/{self.UID}"
        self.pulse_freq = 30
        self._last_pulse_time = time.monotonic()
        self.hardware_status_file = f"/dev/piUART/status/{self.interface}"
        self.qos = 1
        self.retain = False

        if not logger:
            self.logger = RotatingLogger(f"UARTLeafManager-{interface}.log")
        else:
            self.logger = logger
        self.runner = threading.Thread(target=self.loop_runner, args=())
        self.running = False
        self.stopped = True
        self.rxQueue = queue.PriorityQueue(maxsize=1000)
        self.txQueue = queue.PriorityQueue(maxsize=1000)
        parser_list = import_parsers()
        # scan here instead of assigning like below
        match interface:
            case "ttyAMA1":
                parser_name = "intellivue"
            case "ttyAMA2":
                parser_name = "PB840"
            case "ttyAMA3":
                parser_name = "V60"
            case "ttyAMA4":
                parser_name = "PB840_waveforms"
            case _:
                parser_name = ""

        if parser_list.get(parser_name, None):
            self.parser = parser_list[parser_name].parser(
                interface, parent=self.UID, txQueue=self.txQueue
            )
            self.has_valid_parser = True
        else:
            self.parser = default_parser(
                interface, parent=self.UID, txQueue=self.txQueue
            )
            self.has_valid_parser = False
        self.init_pulse()

    def scan_baud(self):
        for brate in self.parser.bauds:
            dg = self.parser.get_uart_data()
            err = self.parser.validate_packet(dg)
            if not err:
                self.baud = brate
                self.parser.set_baud(brate)
                return brate
        self.logger(f"No valid baud found for {self.parser.name}")
        return False

    def process_commands(self, brate):
        # swap baud rate(brate): self.parser.serial_info["brate"]=brate
        # datamode(mode): self.parser.datamode(mode)
        # change send frequency: self.parser.set_frequency()
        # change pulse send freq
        # swap device: self.parser.shutdown, del self.parser, self.parser= new parser, go through the init process
        # immedate pulse: send pulse now
        # update parsers: get a file, hash, etc and update a parser
        # req_id: hand out req_ids for command/responses to work
        # start/stop commands?
        pass

    def loop_start(self):
        # need to add flags here
        self.running = True
        self.stopped = False
        self.runner.start()

    def loop_runner(self):
        # add flags, exception handling
        while self.running:
            while not self.parser.validate_hardware():
                self.find_parser()  # get the next parser in the list
            if self.has_valid_parser and not self.parser.is_running():
                self.parser.loop_start()
            if time.monotonic() > (self._last_pulse_time + self.pulse_freq):
                if not self.txQueue.full():
                    try:
                        # calls to full() do not guarantee space since the leaf may have written or acquired the lock
                        # before the following .put gets called. In the event we try to put when the queue is full because
                        # the leaf wrote the last slot, then put will block until there is space. If in addition to all this
                        # there is a network issue happening and the queue is not emptying, then the program will freeze here forever.
                        self.txQueue.put(self.pulsemsg(), timeout=1)
                        self._last_pulse_time = time.monotonic()
                    except queue.Full:
                        self.logger.critical(
                            "The txQueue is full and a pulse message is lost."
                        )

        self.stopped = True

    def find_parser(self):
        # select the next parser
        pass

    def is_alive(self):
        self.runner.join(timeout=0)
        # should we check the flags?
        return self.runner.is_alive()

    def init_pulse(self):
        self._pulse = {}
        self._pulse["UID"] = self.UID
        self._pulse["parent-node"] = self.parent
        self.pulse()

    def pulse(self):
        self._pulse["DID"] = self.parser.DID
        self._pulse["vent-type"] = self.parser.vent_type
        self._pulse["baud"] = self.parser.baud  # last known good baud
        self._pulse["protocol"] = self.parser.protocol
        self._pulse["device-status"] = self.device_status()
        self._pulse["timestamp"] = str(int(time.time() * 1000))

    def pulsemsg(self):
        self.pulse()
        return (
            3,
            Message(
                topic=self.pulse_topic, payload=json.dumps(self._pulse), qos=self.qos
            ),
        )

    def device_status(self):
        if not self.cable_is_connected():
            return "UNPLUGGED"
        elif not self.parser.status:
            return "PLUGGED_IN"
        else:
            return self.parser.status

    def cable_is_connected(self):
        try:
            with open(self.hardware_status_file, "r") as f:
                hw_status = f.readline().strip().rstrip("\n")
        except:
            hw_status = "?"
        return hw_status[0] == "1"

    def loop_stop(self):
        self.running = False
        ct = 0
        tMAX = 10
        while self.is_alive():
            ct += 1
            time.sleep(0.1)
            if ct > tMAX:
                break

    def enumerate_parsers(self):
        # iterate through ./parsers and add them to a list, also import them all
        pass

    def update_parser(self):
        pass

    def reload_parser(self, sys_name):
        # "parsers.parser1.parser1"
        # first check if you are using this
        importlib.reload(sys.modules[sys_name])


if __name__ == "__main__":
    leaf = UARTLeafManager("ttyAMA2", "123")
    leaf.loop_start()
    while True:
        if leaf.txQueue.not_empty:
            print(f"Recieved {leaf.txQueue.get()}")
        time.sleep(0.5)
