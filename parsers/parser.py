import os, sys
import threading
import time
import queue
import importlib
import serial

# local includes
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger
from tools.MQTT import Message


class parser:
    send_all = 1
    send_named = 2
    send_delta = 3

    def __init__(
        self, tty: str, parent: str, txQueue: queue.PriorityQueue, logger=None
    ):
        if not logger:
            self.logger = RotatingLogger(f"ParserManager-{tty}.log")
        else:
            self.logger = logger
        self.interface = f"/dev/{tty}"
        self.fields = []
        self._stopped = True
        self.serial_info = {}
        self.baud_rates = []
        self.queue = txQueue
        self._poll_freq = 2  # how fast your poll loop runs
        self._send_freq = (
            2  # how fast you want the leaf object to send info down the txqueue
        )
        self._running = False
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
        self.stop_loop()

    def get_uart_data(self, tty, brate, tout, cmd, par=serial.PARITY_NONE, rts_cts=0):
        with serial.Serial(tty, brate, timeout=tout, parity=par, rtscts=rts_cts) as ser:
            ser.flush()
            ser.write(cmd)
            line = ser.readline()
            ser.close()
            return line

    def scan_baud(self):
        for brate in self.baud_rates:
            self.serial_info["brate"] = brate
            dg = self.get_uart_data()
            err = create_packet(dg, debug=True)[1]
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

    def put(self, item):
        if not self.queue.full():
            try:
                self.queue.put(item=item, timeout=2)
                return True
            except queue.Full:
                self.queue.queue.pop()
                return self.put(item)
            except TimeoutError:
                return False
            except:
                return False
        return False


class example_parser(parser):
    def validate_hardware(self):
        return True

    def validate_error_message(self, message):
        return True

    def poll(self):
        self.put((5, Message(payload=f"test{time.time()}", topic="test")))


if __name__ == "__main__":
    q = queue.PriorityQueue(maxsize=3)
    x = example_parser(tty="ttyAMA1", parent="123", txQueue=q)
    x.loop_start()
    while True:
        if q.not_empty:
            print(f"Recieved {q.get()}")
        time.sleep(0.5)
