import os, sys
import threading
import time
import queue
import importlib
import serial
import json
import multiprocessing
import random
from enum import IntEnum, auto

# local includes
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger
from parsers.parser import example_parser, default_parser
from tools.MQTT import Message, MQTTMessage
from parsers.parser import import_parsers

# todo: Every non specific exception catch needs to call Exception as e and log that


class LeafProcessorCommands(IntEnum):
    START = auto()
    STOP = auto()
    TERM = auto()
    ECHO = auto()


class LeafProcessorStates(IntEnum):
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    DEAD = auto()


# todo, integrate this interface to the UARTLeafManager instead?
# we need to rework
class LeafProcessor:
    def __init__(self, connection_type, name, parent):
        self.name = name
        self.parent = parent
        self.connection_type = connection_type
        self.context = multiprocessing.get_context("spawn")
        self.node_transmit_queue = self.context.Queue()
        self.leaf_transmit_queue = self.context.Queue()
        self.command_state_pipe_node, self.command_state_pipe_leaf = self.context.Pipe()
        self.last_state = LeafProcessorStates.STOPPED
        self.processor = self.context.Process(
            target=LeafProcessorRunner,
            args=(
                self.connection_type,
                self.name,
                self.parent,
                self.node_transmit_queue,
                self.leaf_transmit_queue,
                self.command_state_pipe_leaf,
            ),
        )
        time.sleep(1)
        self.processor.start()
        time.sleep(1)
        self.pid = self.processor.pid
        print(self.pid)

    def proc_is_alive(self):
        return self.processor.is_alive()

    def runner_is_alive(self):
        self.state()
        return self.proc_is_alive() and self.last_state != LeafProcessorStates.DEAD

    def transmit(self, message_tuple):
        if not self.node_transmit_queue.full():
            try:
                self.node_transmit_queue.put_nowait(message_tuple)
            except queue.Full:
                return False
            return True
        else:
            return False

    def recieve(self):
        if not self.leaf_transmit_queue.empty():
            try:
                return self.leaf_transmit_queue.get()
            except queue.Empty:
                pass
        else:
            return None

    def full(self):
        return self.node_transmit_queue.full()

    def empty(self):
        return self.leaf_transmit_queue.empty()

    def recQsize(self):
        return self.leaf_transmit_queue.qsize()

    def transQsize(self):
        return self.node_transmit_queue.qsize()

    def start(self):
        try:
            self.command_state_pipe_node.send(LeafProcessorCommands.START)
        except ValueError:
            pass
            # object not  picklable
        # except full?

    def stop(self):
        self.command_state_pipe_node.send(LeafProcessorCommands.STOP)

    def state(self):
        if not self.proc_is_alive():
            self.last_state = LeafProcessorStates.DEAD
            return self.last_state
        if self.command_state_pipe_node.poll(0.01):
            while self.command_state_pipe_node.poll(0.01):
                try:
                    state = self.command_state_pipe_node.recv()  # empty pipe
                    self.last_state = state
                except EOFError:
                    pass  # no more data
                return state
        else:
            self.command_state_pipe_node.send(LeafProcessorCommands.ECHO)
            return self.last_state

    def echo(self):
        self.command_state_pipe_node.send(LeafProcessorCommands.ECHO)

    def join(self, timeout=None):
        t = time.monotonic()
        self.command_state_pipe_node.send(LeafProcessorCommands.TERM)
        if timeout:
            st = time.monotonic()
            timeout = st + timeout
        while True:
            if self.state() == LeafProcessorStates.DEAD:
                break
            if timeout and (time.monotonic() > timeout):
                break
            time.sleep(0.1)
        self.processor.join(0.1)
        print(f"{self.name}.join() Executed {time.monotonic()-t} seconds")
        return self.processor.is_alive()


def LeafProcessorRunner(
    connection_type, name, parent, node_transmit_queue, leaf_transmit_queue, leaf_pipe
):
    match connection_type.upper():
        case "UART":
            leaf = UARTLeafManager(name, parent)
        case "USB":
            leaf = UARTLeafManager(name, parent)
        case "BT":
            raise NotImplementedError
        case "WIFI":
            raise NotImplementedError
        case _:
            raise NotImplementedError
    # todo add logging here
    running = True
    stopped = False
    node_desired_run_state = True
    state = LeafProcessorStates.RUNNING
    leaf_pipe.send(state)
    last_sent_state = state
    while running:
        try:
            # check leaf messages and relay to node
            if not leaf.txQueue.empty():
                while not leaf.txQueue.empty():
                    m = leaf.txQueue.get()  # todo, catch queue exceptions
                    leaf_transmit_queue.put(m)
            # check node messages and relay to leaf
            if not node_transmit_queue.empty():
                while not node_transmit_queue.empty():
                    leaf.rxQueue.put(node_transmit_queue.get())
            # check for node commands
            if leaf_pipe.poll(0.01):
                comm = leaf_pipe.recv()
                match comm:
                    case LeafProcessorCommands.ECHO:
                        leaf_pipe.send(state)
                        last_sent_state = state
                    case LeafProcessorCommands.START:
                        node_desired_run_state = True
                    case LeafProcessorCommands.STOP:
                        node_desired_run_state = False
                    case LeafProcessorCommands.TERM:
                        running = False
                        node_desired_run_state = False
                        leaf.loop_stop()
                        leaf_transmit_queue.put((1, "Accepted term command"))
            # check if leaf needs to be started or stopped
            if node_desired_run_state and state != LeafProcessorStates.RUNNING:
                leaf.loop_start()
                leaf_transmit_queue.put((1, "Accepted start command"))
            elif not node_desired_run_state and state == LeafProcessorStates.RUNNING:
                leaf.loop_stop()
                leaf_transmit_queue.put((1, "Accepted stop command"))
            # update leaf state
            if leaf.running:
                state = LeafProcessorStates.RUNNING
            elif not leaf.running and not leaf.stopped:
                state = LeafProcessorStates.STOPPING
            elif not leaf.running and leaf.stopped:
                state = LeafProcessorStates.STOPPED
            # send state on changes
            if state != last_sent_state:
                leaf_pipe.send(state)
                last_sent_state = state
                leaf_transmit_queue.put((1, f"updated state to {state}"))

        except Exception as e:
            running = False
            try:
                ct = 0
                tMAX = 50
                while not leaf.stopped:
                    ct += 1
                    time.sleep(0.1)
                    if ct > tMAX:
                        break
                    leaf.loop_stop()
            except:
                pass
    leaf_pipe.send(LeafProcessorStates.DEAD)


class fake_leaf:
    def __init__(self, name, parent):
        self.number = random.random() * 5
        self.name = name
        self.rxQueue = queue.PriorityQueue(maxsize=1000)
        self.txQueue = queue.PriorityQueue(maxsize=1000)
        self.running = False
        self.stopped = True
        self.runner = None
        self.loop_start()

    def loop_start(self):
        if not self.running and self.stopped:
            self.running = True
            self.stopped = False
            self.runner = threading.Thread(target=self.loop_runner, args=())
            self.runner.start()

    def loop_stop(self):
        self.running = False
        ct = 0
        tMAX = 10
        while not self.stopped:
            ct += 1
            time.sleep(0.1)
            if ct > tMAX:
                break

    def loop_runner(self):
        # add flags, exception handling
        lastsend = 0
        while self.running:
            if time.monotonic() > (lastsend + self.number):
                try:
                    self.txQueue.put_nowait(
                        (
                            1,
                            f"{self.name}({self.number}) last: {time.monotonic()-lastsend}",
                        )
                    )
                    lastsend = time.monotonic()
                except queue.Full:
                    pass
            while not self.rxQueue.empty():
                try:
                    self.txQueue.put_nowait(
                        (
                            1,
                            f" {self.name} recieved {self.rxQueue.get_nowait()} at {time.monotonic()}",
                        )
                    )
                except queue.Full:
                    pass
                except queue.Empty:
                    pass
            time.sleep(0.1)
        self.stopped = True


class UARTLeafManager:
    # class var
    parsers = {}

    def __init__(self, interface, parentUID, logger=None):
        self.interface = interface
        # self.baud = 9600
        self.parent = parentUID
        self.UID = f"{parentUID}:{interface}"
        self.command_topic = f"Commands/{self.UID}"
        self.response_topic = f"Devices/responses/{self.UID}"
        self.pulse_topic = f"Pulse/leafs/{self.UID}"
        self.pulse_freq = 30
        self.unplugged_pulses_to_skip = 20
        self._unplugged_pulses_skipped = (
            self.unplugged_pulses_to_skip
        )  # counter, set so that it will immediately send
        self._last_pulse_time = time.monotonic()
        self.hardware_status_file = f"/dev/piUART/status/{self.interface}"
        self.qos = 1
        self.retain = False
        self.last_idx = -1
        if not logger:
            self.logger = RotatingLogger(f"UARTLeafManager-{interface}.log")
        else:
            self.logger = logger
        self._last_cable_status = False
        self.check_cable_event()
        self.running = False
        self.stopped = True
        self.rxQueue = queue.PriorityQueue(maxsize=1000)
        self.txQueue = queue.PriorityQueue(maxsize=1000)
        self.startup_pulse()
        self.parser_list = import_parsers()
        self.has_valid_parser = False
        self.ordered_parser_list_keys = list(self.parser_list.keys())
        tmp_baud = None
        tmp_parser = None
        if os.path.exists(f"/usr/src/RTA/config/lastknown-{interface}.txt"):
            with open(f"/usr/src/RTA/config/lastknown-{interface}.txt", "r") as f:
                config = f.readline()
                if not config:
                    pass
                try:
                    parser_name, baud = config.split(":")
                    if parser_name in self.ordered_parser_list_keys:
                        idx = self.ordered_parser_list_keys.index(parser_name)
                        (
                            self.ordered_parser_list_keys[idx],
                            self.ordered_parser_list_keys[0],
                        ) = (
                            self.ordered_parser_list_keys[0],
                            self.ordered_parser_list_keys[idx],
                        )
                    tmp_parser = parser_name
                    tmp_baud = int(baud)
                    self.logger.debug(f"Previous config was {tmp_parser} at {tmp_baud}")
                except:
                    pass
        if self._last_cable_status:
            for self.parser_name in self.ordered_parser_list_keys:
                try:
                    self.parser = self.parser_list[self.parser_name].parser(
                        tty=interface, parent=self.parent, txQueue=self.txQueue
                    )
                    # test_parser.loop_start()
                    self.logger.debug(f"Scanning for {self.parser_name}")
                    if tmp_parser and self.parser_name == tmp_parser and tmp_baud:
                        valid = self.parser.validate_hardware(starting_baud=tmp_baud)
                    else:
                        valid = self.parser.validate_hardware()
                except:
                    valid = False

                if valid:
                    self.has_valid_parser = True
                    self.last_parser_name = self.parser_name
                    nw = True
                    tr = 0
                    if tr < 3:
                        tr = tr + 1
                        try:
                            with open(
                                f"/usr/src/RTA/config/lastknown-{interface}.txt", "w"
                            ) as f:
                                f.write(f"{self.parser_name}:{self.parser.baud}")
                            nw = False
                        except FileNotFoundError:
                            os.mkdir("/usr/src/RTA/config/")
                            self.logger.info(
                                "config directory not found, making it now at /usr/src/RTA/config/"
                            )
                        except:
                            self.logger.info(
                                "Failed to write the detected configuration to the config folder."
                            )

                    break
                else:
                    self.destroy_parser()

                # else continue to next parser
        if not self.has_valid_parser:
            self.parser_name = "GENERIC"
            self.last_parser_name = self.parser_name
            self._unplugged_pulses_skipped = self.unplugged_pulses_to_skip
            self.parser = default_parser(
                interface, parent=self.UID, txQueue=self.txQueue
            )
        self.init_pulse()
        self.loop_start()

    def destroy_parser(self, assign_generic=True):
        try:
            self.parser.__del__()
        except:
            pass
        try:
            del self.parser
        except:
            pass

        self.has_valid_parser = False
        if assign_generic:
            self.parser_name = "GENERIC"
            self._unplugged_pulses_skipped = self.unplugged_pulses_to_skip
            self.parser = default_parser(
                self.interface, parent=self.parent, txQueue=self.txQueue
            )

    """ def scan_baud(self):
        for brate in self.parser.bauds:
            dg = self.parser.get_uart_data()
            err = self.parser.validate_packet(dg)
            if not err:
                self.parser.baud = brate
                self.parser.set_baud(brate)
                return brate
        self.logger(f"No valid baud found for {self.parser.name}")
        return False"""

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
        if not self.running and self.stopped:
            self.parser.loop_start()
            self.running = True
            self.stopped = False
            self.runner = threading.Thread(target=self.loop_runner, args=())
            self.runner.start()

    def check_cable_event(self):
        if self.cable_is_connected() != self._last_cable_status:
            self._last_cable_status = not self._last_cable_status
            self.logger.debug(
                f"Detected a "
                + ("new connection." if self._last_cable_status else "disconnection.")
            )
            return True
        return False

    def loop_runner(self):
        # add flags, exception handling
        while self.running:
            try:
                cable_event = self.check_cable_event()
                if self._last_cable_status:
                    if (
                        not self.parser.validate_hardware()
                        or self.parser.status == "DISCONNECTED"
                    ):
                        self.find_parser()  # get the next parser in the list
                    if self.has_valid_parser:
                        if not self.parser.is_running():
                            self.parser.loop_start()
                elif cable_event:
                    self.destroy_parser()
                if time.monotonic() > (self._last_pulse_time + self.pulse_freq):
                    if (
                        self.parser_name == "GENERIC"
                        and self._unplugged_pulses_skipped
                        < self.unplugged_pulses_to_skip
                    ):
                        self._unplugged_pulses_skipped = (
                            1 + self._unplugged_pulses_skipped
                        )
                    else:
                        self._unplugged_pulses_skipped = 0
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
                time.sleep(0.1)
            except Exception as e:
                self.logger.critical(f"Exception has occured in main leaf loop: {e}")
                self.running = False
        try:
            self.destroy_parser()
        except Exception as e:
            self.logger.critical(
                f"Exception occured trying to stop the parser, parser may not be stopped. \n{e}"
            )
        self.stopped = True

    def find_parser(self):
        # if there once existed a parser, try it again on a reconnect
        if self.last_parser_name in self.ordered_parser_list_keys:
            idx = self.ordered_parser_list_keys.index(self.last_parser_name)
        # else use the next parser in the list
        else:
            idx = self.last_idx + 1
        if idx >= len(self.ordered_parser_list_keys):
            idx = 0
        self.last_idx = idx
        self.parser_name = self.ordered_parser_list_keys[idx]
        self.destroy_parser(assign_generic=False)
        try:
            self.logger.debug(f"Scanning for {self.parser_name}")
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
            self.destroy_parser(assign_generic=False)
        if not self.has_valid_parser:
            self.parser_name = "GENERIC"
            self._unplugged_pulses_skipped = self.unplugged_pulses_to_skip
            self.parser = default_parser(
                self.interface, parent=self.parent, txQueue=self.txQueue
            )
        self.last_parser_name = self.parser_name
        return False

    def is_alive(self):
        self.runner.join(timeout=0)
        # should we check the flags?
        # self.running, self.stopped, condition
        # 0,1 : not running
        # 1,0 : running
        # 0,0 : kill command was sent, but runner has not finished last loop
        # 1,1 : invalid error condition
        return self.runner.is_alive()

    def startup_pulse(self):
        pulsemsg = {
            "UID": self.UID,
            "ParentNode": self.parent,
            "DID": "Not acquired yet",
            "VentType": "NA",
            "Baud": 0,
            "Protocol": "Not acquired yet",
            "DeviceStatus": "INITIALIZING",
            "Timestamp": str(int(time.time() * 1000)),
        }
        self.txQueue.put(self.pulsemsg(pulsemsg), timeout=1)
        self._last_pulse_time = time.monotonic() - 30

    def init_pulse(self):
        self._pulse = {}
        self._pulse["UID"] = self.UID
        self._pulse["ParentNode"] = self.parent
        self.pulse()

    def pulse(self):
        self._pulse["DID"] = self.parser.DID
        self._pulse["VentType"] = (
            self.parser.vent_type if self.has_valid_parser else "NA"
        )
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

    def pulsemsg(self, override=None):
        if not override:
            self.pulse()
            payload = json.dumps(self._pulse)
        # elif isinstance(override,tuple)
        # elif string
        elif isinstance(override, dict):
            payload = json.dumps(override)
        else:
            payload = str(override)
        return (
            3,
            Message(topic=self.pulse_topic, payload=payload, qos=self.qos),
        )

    def device_status(self):
        if not self.cable_is_connected():
            return "UNPLUGGED"
        elif not self.parser.status:
            return "PLUGGED_IN"
        else:
            return self.parser.status

    def cable_is_connected(self):
        ret = False
        for _ in range(3):
            try:
                with open(self.hardware_status_file, "r") as f:
                    hw_status = f.readline().strip().rstrip("\n")
                ret = hw_status[0] == "1"
                break
            except Exception as e:
                hw_status = "?"
        return ret

    def txempty(self):
        return not self.txQueue.not_empty

    def rxfull(self):
        return self.rxQueue.full()

    def get(self):
        try:
            return self.txQueue.get_nowait()
        except queue.Empty:
            return (None, None)

    def put(self, message, priority=None):
        if priority and isinstance(message, tuple):
            message[0] = priority
        elif priority and isinstance(message, (MQTTMessage, Message)):
            message = (priority, message)
        elif not priority and isinstance(message, tuple):
            pass
        elif not priority and isinstance(message, (MQTTMessage, Message)):
            message = (5, message)
        else:
            return False
        try:
            self.rxQueue.put_nowait(message)
            return True
        except queue.Full:
            return False

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
    leaf = UARTLeafManager("ttyAMA1", "123")
    # leaf.loop_start()
    puls, vits = [time.time() * 1000, 0, 0], [time.time() * 1000, 0, 0]  # last,ct,avg
    count = 0
    start = time.monotonic()
    lastt = start
    loopexecutiontimes = []
    while True:
        count += 1
        if not leaf.txempty():
            _, message = leaf.get()
            if message:
                m = message
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
        # if count > 20:
        # print(f"uptime {time.monotonic()-start}")
        # break
        # else:
        time.sleep(0.5)
        now = time.monotonic()
        print(f"loop execution {now-lastt}")
        loopexecutiontimes.append(now - lastt)
        lastt = now
    try_to_kill = time.monotonic()
    while not leaf.stopped:
        leaf.loop_stop()
    print(f"Took {time.monotonic()-try_to_kill} to shutdown")
    print(loopexecutiontimes)
    pass
