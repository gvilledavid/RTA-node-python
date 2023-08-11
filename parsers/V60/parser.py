import os, sys, time
import json
import serial

# from parser folder
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
)  # add RTA-node-python to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path

from PB840.PB840_datagram import datagrams
from PB840.PB840_data_to_packet import create_packet

# from PB840_serial import get_ventilator_data
from PB840.PB840_fields import PB840_BAUD_RATES


import parsers.parser
from tools.MQTT import Message


# 'PB840.PB840': <module 'PB840.PB840' from 'C:\\Users\\Srazo\\Documents\\GitHub\\RTA-node-python\\parsers\\PB840\\PB840.py'>, 'parsers.PB840': <module 'parsers.PB840' from 'C:\\Users\\Srazo\\Documents\\GitHub\\RTA-node-python\\parsers\\PB840\\__init__.py'>, 'parsers.PB840.PB840': <module 'parsers.PB840.PB840' from 'C:\\Users\\Srazo\\Documents\\GitHub\\RTA-node-python\\parsers\\PB840\\PB840.py'>}
# package="PB840"
# new_parser=sys.modules[f"parsers.{package}"].parser(*args)
class parser(parsers.parser.parser):
    def _init(self):
        # super calls _init at the end of its constructor, _init overwritable by child
        # dont overwrite __init__, or if you do, call super.__init__ as the first thing
        # in child constructor
        self.name = "PB840"
        self.DID = ""
        self.vent_type = ""
        self.baud = 9600  # todo, load this from config file for last known good
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
        self.vitals_topic = f"Device/vitals/{self.UID}"
        self.settings_priority = 7
        self.settings_topic = f"Device/settings/{self.UID}"
        self.legacy_topic = f"Device/vitals/{self.UID.replace(self.interface,'').strip(':').lower()}LeafMain1"
        self.qos = 1
        self.send_legacy = True
        # self.fields will  be parsers.parser.send_all
        #    or parser.send_delta
        #    or parser.send_named
        self._last_send = 0
        self.last_packet = {}
        self.publish()

    def poll(self):
        self.publish()

    # scan_brate method needs to either be overwritten or validate_packet needs to be implemented
    def validate_packet(dg):
        pass

    def parse(self):
        pass

    def validate_hardware(self):
        # return true if real vent is detected
        pass

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
        if 4 <= len(self.serial_info):
            dg = self.get_uart_data(debug=True)
            msg, err = create_packet(dg, debug=True)
        else:
            msg, err = create_packet(datagrams[0], debug=True)
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
                vit["timestamp"] = str(int(time.time() * 1000))
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
                sets["timestamp"] = str(int(time.time() * 1000))
                responses.append(
                    self.put(
                        self.settings_priority,
                        Message(
                            topic=self.settings_topic,
                            payload=vit,
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

            self.put()
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
            self.packets_since_last_failure = 0
        else:
            self.packets_since_last_failure += 1
            print(
                f"{self.total_count-self.success_count}/{self.total_count} Failed to send message to topic {topic}"
            )
            if self.packets_since_last_failure > 10:
                self.scan_brate()
                self.packets_since_last_failure = 0
        return success_count

    def publish(self):
        self.success_count = 0
        self.total_count = 0

        if self._last_send + self._send_freq > time.time():
            return
        # self.set_send_freq() from parent to update _send_freq time
        self.total_count += 1

        msg, result = self.send_message()
        self.success_count = self.report_status(
            msg, result, self.success_count, self.total_count
        )
