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
        self.baud = 9600
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

        self.running = False
        self.stopped = True
        self.rxQueue = queue.PriorityQueue(maxsize=1000)
        self.txQueue = queue.PriorityQueue(maxsize=1000)
        self.parser_list = import_parsers()
        self.has_valid_parser = False
        self.ordered_parser_list_keys = list(self.parser_list.keys())
        if os.path.exists(f"/usr/src/RTA/config/lastknown-{interface}.txt"):
            with open(f"/usr/src/RTA/config/lastknown-{interface}.txt", "r") as f:
                config = f.readline()
                if not config:
                    pass
                try:
                    parser_name, self.baud = config.split(":")
                    if parser_name in self.ordered_parser_list_keys:
                        idx = self.ordered_parser_list_keys.index(parser_name)
                        (
                            self.ordered_parser_list_keys[idx],
                            self.ordered_parser_list_keys[0],
                        ) = (
                            self.ordered_parser_list_keys[0],
                            self.ordered_parser_list_keys[idx],
                        )
                    self.baud = int(self.baud)
                except:
                    pass
        for self.parser_name in self.ordered_parser_list_keys:
            try:
                self.parser = self.parser_list[self.parser_name].parser(
                    tty=interface, parent=self.parent, txQueue=self.txQueue
                )
                # test_parser.loop_start()
                valid = self.parser.validate_hardware(starting_baud=self.baud)
            except:
                valid = False

            if valid:
                self.has_valid_parser = True
                with open(f"/usr/src/RTA/config/lastknown-{interface}.txt", "w") as f:
                    f.write(f"{self.parser_name}:{self.parser.baud}")
                break
            else:
                try:
                    del self.parser
                except:
                    pass
            # else continue to next parser
        if not self.has_valid_parser:
            self.parser = default_parser(
                interface, parent=self.UID, txQueue=self.txQueue
            )
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
        self.parser.loop_start()
        self.running = True
        self.stopped = False
        self.runner = threading.Thread(target=self.loop_runner, args=())
        self.runner.start()

    def loop_runner(self):
        # add flags, exception handling
        while self.running:
            if not self.parser.validate_hardware():
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
        if self.parser_name in self.ordered_parser_list_keys:
            idx = self.ordered_parser_list_keys.index(self.parser_name) + 1
            if idx >= len(self.ordered_parser_list_keys):
                idx = 0
        else:
            idx = 0
        self.parser_name = self.ordered_parser_list_keys[idx]
        try:
            del self.parser
        except:
            pass
        try:
            self.parser = self.parser_list[self.parser_name].parser(
                tty=self.interface, parent=self.parent, txQueue=self.txQueue
            )
            valid = self.parser.validate_hardware()
        except:
            valid = False

        if valid:
            self.has_valid_parser = True
            with open(f"/usr/src/RTA/config/lastknown-{self.interface}.txt", "w") as f:
                f.write(f"{self.parser_name}:{self.parser.baud}")
            return True
        else:
            try:
                del self.parser
            except:
                pass
        if not self.has_valid_parser:
            self.parser = default_parser(
                self.interface, parent=self.parent, txQueue=self.txQueue
            )
        return False

    def is_alive(self):
        self.runner.join(timeout=0)
        # should we check the flags?
        return self.runner.is_alive()

    def init_pulse(self):
        self._pulse = {}
        self._pulse["UID"] = self.UID
        self._pulse["ParentNode"] = self.parent
        self.pulse()

    def pulse(self):
        self._pulse["DID"] = self.parser.DID
        self._pulse["VentType"] = self.parser.vent_type
        self._pulse["Baud"] = self.parser.baud  # last known good baud
        self._pulse["Protocol"] = self.parser.protocol
        self._pulse["DeviceStatus"] = self.device_status()
        self._pulse["Timestamp"] = str(int(time.time() * 1000))
        if self.parser.name == "Intellivue":
            try:
                self._pulse["BedName"] = self.parser.intellivue.bedlabel
                self._pulse["MDSstatus"] = self.parser.intellivue.status
                self._pulse["MDSmode"] = self.parser.intellivue.mode
            except:
                pass
        else:
            self._pulse.pop("BedName", None)
            self._pulse.pop("MDSstatus", None)
            self._pulse.pop("MDSmode", None)

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
    leaf = UARTLeafManager("ttyAMA4", "123")
    leaf.loop_start()
    puls, vits = [time.time() * 1000, 0, 0], [time.time() * 1000, 0, 0]  # last,ct,avg
    while True:
        if leaf.txQueue.not_empty:
            m = leaf.txQueue.get()[1]
            print(f"Recieved {m}")
            if m.topic[0] == "P":
                last = puls[0]
                puls[0] = int(m.dict()["Timestamp"])
                puls[1] = puls[1] + 1
                puls[2] = (puls[2] * (puls[1] - 1) + (puls[0] - last)) / puls[1]
                print(
                    f"**********Pulse : delta {(puls[0]-last)/1000}, avg {puls[2]/1000}"
                )
            if m.topic[0] == "D":
                last = vits[0]
                vits[0] = int(m.dict()["Timestamp"])
                vits[1] = vits[1] + 1
                vits[2] = (vits[2] * (vits[1] - 1) + (vits[0] - last)) / vits[1]
                print(
                    f"**********Vitals: delta {(vits[0]-last)/1000}, avg {vits[2]/1000}"
                )
        time.sleep(0.5)
