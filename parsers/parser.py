import os, sys
import threading
import time
import queue
import importlib
import serial
import random

# local includes
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger
from tools.MQTT import Message


def get_parser_folder():
    return os.path.dirname(os.path.realpath(__file__))


def enumerate_parsers():
    PARSER_FOLDER = get_parser_folder()
    return [
        potential_parser
        for potential_parser in os.listdir(PARSER_FOLDER)
        if os.path.isdir(os.path.join(PARSER_FOLDER, potential_parser))
        and not (potential_parser[0] == "_")
    ]


def import_parsers():
    PARSER_FOLDER = get_parser_folder()
    if PARSER_FOLDER not in sys.path:
        sys.path.append(PARSER_FOLDER)
    return {x: importlib.import_module(f"{x}.parser") for x in enumerate_parsers()}


# use like x[0].parser("ttyAMA1","123",queue)


def reimport_parsers():
    PARSER_FOLDER = get_parser_folder()
    importlib.invalidate_caches()
    imported_parsers = []
    for x in enumerate_parsers():
        # if x in sys.modules:
        #    imported_parsers.append(importlib.reload( ...))
        # else:
        #    imported_parsers.append(importlib.import_module("parser.parser",x))
        pass
    return imported_parsers


class parser:
    send_all = 1
    send_named = 2
    send_delta = 3
    parsers_count = 0
    parsers_in_use = {}
    plock = threading.Lock()

    @classmethod
    def register_parser(obj, parser_class):
        with obj.plock:
            id = obj.parsers_count
            obj.parsers_count += 1
        obj.parsers_in_use[id] = parser_class
        return id

    @classmethod
    def deregister_parser(obj, id):
        is_valid = obj.parsers_in_use.get(id, None)
        if is_valid:
            del obj.parsers_in_use[id]
            return True
        return False

    def reload_parser(obj, id):
        pass

    def __init__(
        self, tty: str, parent: str, txQueue: queue.PriorityQueue, logger=None
    ):
        if not logger:
            self.logger = RotatingLogger(f"ParserManager-{tty}.log")
        else:
            self.logger = logger

        if tty[0:2].upper() == "COM":  # windows-like
            self.interface = tty
        else:
            self.interface = f"/dev/{tty}"
        self.fields = []
        self._stopped = True

        self.baud_rates = []
        self.queue = txQueue
        self._poll_freq = 2  # how fast your poll loop runs
        self._send_freq = 2  # how fast the leaf will send info down the txqueue

        self._running = False

        # pulse info:
        self.status = "INITIALIZING"  # change to MONITORING, STANDBY, or others
        self.DID = ""
        self.vent_type = ""
        self.baud = 9600
        self.protocol = ""
        self.serial_info = {
            "tty": self.interface,
            "brate": self.baud,
            "tout": 2,
            "cmd": "",
            "par": serial.PARITY_NONE,
            "rts_cts": 0,
        }
        self.UID = f"{parent}:{tty}"
        self._init()

    def _init(self):
        """
        user init for the specific parser
        """
        pass

    def _del(self):
        """
        user destructor for the specific parser
        """
        pass

    def __del__(self):
        self.loop_stop()

    def get_uart_data(self, debug=False):
        if debug:
            time.sleep(2 * random.random())
            return b"MISCF,1225,169 ,\x0216:02 ,840 3510072467    ,APR 04 2023 ,INVASIVE ,A/C   ,VC    ,      ,V-Trig,9.0   ,1.520 ,120.0 ,21    ,      ,8.0   ,0.0   ,20    ,0.580 ,10.0  ,70.0  ,100   ,      ,      ,RAMP  ,VC    ,      ,      ,      ,SQUARE,OFF   ,51    ,      ,24.500,0.470 ,1900  ,OFF   ,1900  ,OFF   ,OFF   ,      ,10.3  ,8.8   ,      ,      ,      ,      ,         ,      ,      ,HME               ,      ,Disabled ,20    ,      ,      ,      ,43.0  ,      ,      ,      ,      ,      ,ADULT    ,      ,      ,30.0  ,9.0   ,1.312 ,11.800,30.0  ,11.0  ,7.80  ,1:7.80,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,7.9   ,      ,      ,0.0   ,0.0   ,0.0   ,0.0   ,0.0   ,      ,133.0 ,5.3   ,      ,85.0  ,0.0   ,      ,0.0   ,0.0   ,0.000 ,OFF   ,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,LOW   ,NORMAL,NORMAL,NORMAL,NORMAL,RESET ,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,NORMAL,      ,      ,OFF   ,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,      ,\x03\r"
        with serial.Serial(
            port=self.serial_info["tty"],
            baudrate=self.serial_info["brate"],
            timeout=self.serial_info["tout"],
            parity=self.serial_info["par"],
            rtscts=self.serial_info["rts_cts"],
        ) as ser:
            ser.flush()
            ser.write(self.serial_info["cmd"])
            line = ser.readline()
            ser.close()
            return line

    def set_baud(self, brate):
        self.serial_info["brate"] = brate

    def scan_baud(self):
        for brate in self.baud_rates:
            self.serial_info["brate"] = brate
            dg = self.get_uart_data()
            err = self.create_packet(dg, debug=True)[1]
            if not err:
                return
        print("no valid baud rate found")

    def validate_hardware(self):
        raise NotImplemented(
            "You must overwrite validate_hardware method to return true if the connected device is correct."
        )

    def validate_error_message(self, message):
        raise NotImplemented(
            "You must implement validate_error_message to return true if the parser"
        )

    def loop_start(self):
        self.thread = threading.Thread(target=self.runner, args=())
        self._running = True
        self._stopped = False
        self.thread.start()

    def runner(self):
        while self._running:
            self.poll()
            time.sleep(self._poll_freq)

        self._stopped = True

    def is_running(self):
        return self._running

    def poll(self):
        raise NotImplemented("Overwrite .poll() with your loop code for this parser.")

    def loop_stop(self):
        self._running = False
        self.thread.join(self._timeout)
        del self.thread

    def set_baud_rate(self, brate):
        self.baud = brate

    def enable_fields(self, mode):
        """
        .poll() must use this and send the appropriate data from this mode
        """
        if (
            mode != parser.send_all
            or mode != parser.send_delta
            or mode != parser.send_named
        ):
            raise ValueError(
                f"mode in enable_fields is {type(mode)} and should be parser.send_all or send_delta or send_named"
            )
        self.fields = mode

    def set_send_freq(self, seconds):
        self._send_freq = seconds

    def set_poll_freq(self, seconds):
        self._poll_freq = seconds

    def put(self, priority, item):
        if not self.queue.full():
            try:
                self.queue.put(item=(priority, item), timeout=2)
                return True
            except queue.Full:
                self.queue.queue.pop()
                return self.put(priority, item)
            except TimeoutError:
                return False
            except:
                return False
        return False

    def datamode(self, mode):
        match mode:
            case "send_all":
                self.mode = parser.send_all
            case "send_named":
                self.mode = parser.send_named
            case "send_delta":
                self.mode = parser.send_delta


class example_parser(parser):
    def validate_hardware(self):
        return True

    def validate_error_message(self, message):
        return True

    def poll(self):
        self.put((5, Message(payload=f"test{time.time()}", topic="test")))

    def stop_loop(self):
        pass


class default_parser(parser):
    def _init(self):
        self.name = "Empty parser"
        self.DID = "NA"
        self.vent_type = ""
        self.baud = 0
        self.protocol = ""
        self.serial_info = {
            "tty": self.interface,
            "brate": self.baud,
            "tout": 0.5,
            "cmd": b"SNDF\r",
            "par": serial.PARITY_NONE,
            "rts_cts": 0,
        }
        self.vitals_priority = 6
        self.vitals_topic = f"Devices/vitals/{self.UID}"
        self.settings_priority = 7
        self.settings_topic = f"Devices/settings/{self.UID}"
        self.legacy_topic = f"Device/vitals/{self.UID.replace(self.interface,'').strip(':').lower()}LeafMain1"
        self.qos = 1
        self.send_legacy = True
        self.status = ""
        self.bauds = [9600, 19200, 38400, 115200]
        # self.fields will  be parsers.parser.send_all
        #    or parser.send_delta
        #    or parser.send_named
        self._last_send = 0
        self.last_packet = {}

    def poll(self):
        if self._last_send + self._send_freq > time.monotonic():
            self._last_send = time.monotonic()
            self.put(
                5,
                Message(
                    payload=f'\{"UID":"{self.UID}","timestamp":"{str(int(time.time()*1000))}"\}',
                    topic=self.settings_topic,
                ),
            )

    def validate_hardware(self):
        return True

    def validate_error_message(self, message):
        return True

    def stop_loop(self):
        pass


if __name__ == "__main__":
    q = queue.PriorityQueue(maxsize=3)
    x = import_parsers()
    print(x)
    p = x["PB840"].parser(tty="ttyAMA1", parent="123", txQueue=q)
    p.loop_start()
    while True:
        if q.not_empty:
            print(f"Recieved {q.get()}")
        time.sleep(0.5)
