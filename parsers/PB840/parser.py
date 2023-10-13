import os, sys, time
import json
import serial
import queue

# from parser folder
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
)  # add RTA-node-python to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path

from PB840.PB840_datagram import datagrams
from PB840 import PB840_data_to_packet

# from PB840_serial import get_ventilator_data
from PB840.PB840_fields import PB840_BAUD_RATES, PB840_CHECKSUM


import parsers.parser
from tools.MQTT import Message, MQTT


# 'PB840.PB840': <module 'PB840.PB840' from 'C:\\Users\\Srazo\\Documents\\GitHub\\RTA-node-python\\parsers\\PB840\\PB840.py'>, 'parsers.PB840': <module 'parsers.PB840' from 'C:\\Users\\Srazo\\Documents\\GitHub\\RTA-node-python\\parsers\\PB840\\__init__.py'>, 'parsers.PB840.PB840': <module 'parsers.PB840.PB840' from 'C:\\Users\\Srazo\\Documents\\GitHub\\RTA-node-python\\parsers\\PB840\\PB840.py'>}
# package="PB840"
# new_parser=sys.modules[f"parsers.{package}"].parser(*args)
class parser(parsers.parser.parser):
    def _init(self):
        # super calls _init at the end of its constructor, _init overwritable by child
        # dont overwrite __init__, or if you do, call super.__init__ as the first thing
        # in child constructor
        self.name = "DCI"
        self.DID = ""
        self.vent_type = ""
        self.baud = 9600  # todo, load this from config file for last known good
        self.baud_rates = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
        self.baud_rates.sort(reverse=True)
        self.protocol = ""
        self.serial_info = {
            "tty": self.interface,
            "brate": self.baud,
            "tout": 0.5,
            "cmd": b"SNDF\r",
            "par": serial.PARITY_NONE,
            "rts_cts": 0,
            "expected_bits": 2 * PB840_CHECKSUM[0] * 8,
        }
        self.vitals_priority = 6
        self.vitals_topic = f"Devices/vitals/{self.UID}"
        self.settings_priority = 7
        self.settings_topic = f"Devices/settings/{self.UID}"
        self.legacy_topic = f"Device/Vitals/{self.UID.replace(self.interface,'').strip(':').lower()}LeafMain1"
        self.qos = 1
        self.send_legacy = False
        # self.fields will  be parsers.parser.send_all
        #    or parser.send_delta
        #    or parser.send_named
        self._last_send = time.monotonic()
        self.last_packet = {}
        self.success_count = 0
        self.total_count = 0
        self.was_connected = False
        self._send_freq = 6
        self._poll_freq = 2
        self.packets_since_last_failure = 0
        self._max_error_count = 5

    def poll(self):
        if self.was_connected:
            if self._last_send + self._send_freq > time.monotonic():
                return
            # self.set_send_freq() from parent to update _send_freq time
            self.total_count += 1

            msg, result = self.send_message()
            self.success_count = self.report_status(
                msg, result, self.success_count, self.total_count
            )
        else:
            print("not connected, attempting...")
            self.logger.info("not connected, attempting...")
            if not self.validate_hardware():
                self.status = "DISCONNECTED"

    # scan_brate method needs to either be overwritten or validate_packet needs to be implemented
    def validate_packet(self, dg):
        try:
            data = PB840_data_to_packet.get_data_as_fields(dg)
            vent_type = int(data[4][1][0:3])
            if vent_type in [840, 980]:
                self.vent_type = data[4][1][0:3]
                self.DID = data[4][1][4:]
                self.was_connected = True
                self.baud = self.serial_info["brate"]
                self.status = "MONITORING"
                return data, True
        except Exception as e:
            pass

        self.was_connected = False
        self.status = "NOT COMMUNICATING"
        return {}, False

    def parse(self):
        pass

    def validate_hardware(self, starting_baud=None):
        # return true if real vent is detected
        # dg,err =self.get_uart_data()
        if not starting_baud and self.was_connected:
            return self.validate_hardware(self.baud)
        if starting_baud:
            if starting_baud in self.baud_rates:
                idx = self.baud_rates.index(starting_baud)
                if idx:
                    self.baud_rates[0], self.baud_rates[idx] = (
                        self.baud_rates[idx],
                        self.baud_rates[0],
                    )
            else:
                self.baud_rates.insert(0, starting_baud)

        return self.scan_baud()

    def check_deltas(self, msg):
        lp = self.last_packet
        lp = lp.get("l", [])
        lp = {i["n"]: i["v"] for i in lp}

        cp = msg.get("l", [])
        cp = {i["n"]: i["v"] for i in cp}

        diffs = {k: cp[k] for k in cp if not (k in lp and cp[k] == lp[k])}

        self.last_packet = msg
        print("packet differences = ", diffs)

    def send_message(self):
        # respect self.mode setting when building packet
        dg, status = self.get_uart_data(debug=False)
        msg = ""
        if status:
            msg, err = PB840_data_to_packet.create_packet(dg, debug=False)
        else:
            err = True
        if not err:
            # todo: refactor this mess
            if not err:
                vit = {}
                sets = {}
                settings = [
                    "VtID",
                    "Type",
                    "Mode",
                    "MType",
                    "SType",
                    "SetRate",
                    "SetVT",
                    "PFlow",
                    "SetFlow",
                    "SetFIO2",
                    "SetPEEP",
                    "SetPSV",
                    "SetP",
                    "SetTi",
                    "PBW",
                ]
                vitals = [
                    "Pplat",
                    "TotBrRate",
                    "VTe",
                    "MinVent",
                    "PIP",
                    "Ti",
                    "VTi",
                    "PEEPi",
                    "RSBI",
                    "TiTtot",
                    "PEEP",
                    "Raw",
                    "NIF",
                    "fspon",
                ]
                # todo:do this before you convert to the legacy format
                for v in msg.get("l", []):
                    if v["n"] in vitals:
                        vit[v["n"]] = v["v"]
                    if v["n"] in settings:
                        sets[v["n"]] = v["v"]
                self.vitals_topic
                # build message packets with their priority and send to leaf txQueue
                vit["UID"] = self.UID
                vit["Timestamp"] = str(int(time.time() * 1000))
                responses = []
                responses.append(
                    self.put(
                        self.vitals_priority,
                        Message(
                            topic=self.vitals_topic,
                            payload=vit,
                            qos=self.qos,
                            retain=False,
                        ),
                    )
                )

                sets["UID"] = self.UID
                sets["Timestamp"] = str(int(time.time() * 1000))
                responses.append(
                    self.put(
                        self.settings_priority,
                        Message(
                            topic=self.settings_topic,
                            payload=sets,
                            qos=self.qos,
                            retain=False,
                        ),
                    )
                )
                if self.send_legacy:
                    responses.append(
                        self.put(
                            10,
                            Message(
                                topic=self.legacy_topic,
                                payload=msg,
                                qos=self.qos,
                                retain=False,
                            ),
                        )
                    )

                return msg, [-1 if False in responses else 0]

            # self.put()
        else:
            return msg, [-1]

    def report_status(self, msg, result, success_count, total_count):
        status = result[0]
        if status == 0:
            self.check_deltas(msg)
            self.success_count += 1
            print(
                f"{self.success_count}/{self.total_count} Send at`{msg['v']}` to topic `{self.legacy_topic}`"
            )
            packets_since_last_failure = 0
            self._last_send = time.monotonic()
        else:
            self.packets_since_last_failure += 1
            print(
                f"{self.total_count-self.success_count}/{self.total_count} Failed to send message to topic {self.legacy_topic}"
            )
            if self.packets_since_last_failure > self._max_error_count:
                print("Failed too many times, scanning baud rate...")
                self.logger.info("Failed too many times, scanning baud rate...")
                if not self.validate_hardware():
                    self.status = "DISCONNECTED"
                self.packets_since_last_failure = 0
        return success_count


if __name__ == "__main__":
    q = queue.PriorityQueue(maxsize=3)
    x = parsers.parser.import_parsers()
    print(f"All parsers available: {x}")
    p = x["PB840"].parser(tty="ttyAMA3", parent="123", txQueue=q)
    if p.validate_hardware():
        print("valid vent detected")
    p.loop_start()
    last_status = None
    while True:
        if q.not_empty:
            print(f"\n\n\n\n\nRecieved {q.get()}\n\n\n\n\n")
        time.sleep(0.1)
        if last_status != p.status:
            print("\n\n\n\n\n" + p.status + "\n\n\n\n\n")
            last_status = p.status
