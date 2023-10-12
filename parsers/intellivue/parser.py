# Adapted from: https://www.emqx.com/en/blog/how-to-use-mqtt-in-python

import random
import time
import paho.mqtt.client as mqtt
import ssl
import json
import traceback
import subprocess
import serial, os, sys
import queue
import debugpy

# from parser folder
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
)  # add RTA-node-python to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path


import parsers.parser
from tools.MQTT import Message, MQTT
from parsers.intellivue.ivue import Intellivue


class parser(parsers.parser.parser):
    def _init(self):
        # scan baud rate here?
        self.name = "Intellivue"
        self.DID = ""
        self.vent_type = "Intellivue"
        self.baud = 115200
        self.protocol = "MIB"
        self.serial_info = {
            "tty": self.interface,
            "brate": self.baud,
            "tout": 0.5,
            "cmd": "",
            "par": serial.PARITY_NONE,
            "rts_cts": 0,
        }
        tty = self.interface.split("/")[-1]
        print(tty)
        self._poll_freq = 0.2
        self._send_freq = 10
        self.logger.debug("Starting Intellivue")
        self.intellivue = Intellivue(
            ttyDEV=tty,
            ttyBaud=self.serial_info["brate"],
            mac=self.parent,
            logger=self.logger,
        )

        self.last_packet = {"last_time": time.time()}
        self.vitals_priority = 6
        self.vitals_topic = f"Devices/vitals/{self.UID}"
        self.settings_priority = 7
        self.settings_topic = f"Devices/settings/{self.UID}"
        self.legacy_topic = f"Device/Vitals/{self.UID.replace(self.interface,'').strip(':').lower()}LeafMain1"
        self.qos = 1
        self.send_legacy = True
        # self.fields will  be parsers.parser.send_all
        #    or parser.send_delta
        #    or parser.send_named
        self._last_send = time.monotonic() - 10
        self._last_recieved_packet = ""
        self._last_recieved_pulse = ""
        self._last_legacy_message = Message(
            payload={"n": "v", "l": [], "v": 0}, topic=self.legacy_topic
        )

    def check_deltas(self, msg):
        lp = self.last_packet
        lp = lp.get("l", [])
        lp = {i["n"]: i["v"] for i in lp}

        cp = msg.get("l", [])
        cp = {i["n"]: i["v"] for i in cp}

        diffs = {k: cp[k] for k in cp if not (k in lp and cp[k] == lp[k])}

        self.last_packet = msg
        self.last_packet["last_time"] = time.time()
        print("packet differences = ", diffs)

    def poll(self):
        if self.intellivue.connected:
            packet, err = self.intellivue.poll()
            self.status = self.intellivue.mode
            if packet:
                self.put(
                    self.vitals_priority,
                    Message(topic=self.vitals_topic, payload=packet),
                )
                self._last_send = time.monotonic()
            """if packet:
                self._last_recieved_packet = packet
                self._last_legacy_message = Message(
                    payload=self.intellivue.legacy_vitals,
                    topic=self.intellivue.legacy_vitals_topic,
                )
                pulse_topic, pulse_message = self.intellivue.pulse()
                self._last_recieved_pulse = pulse_message
                self.status = self.intellivue.status
            if self._last_recieved_packet and (
                self._last_send + self._send_freq < time.monotonic()
            ):
                self.put(
                    self.vitals_priority,
                    Message(
                        topic=self.vitals_topic, payload=self._last_recieved_packet
                    ),
                )
                self._last_send = time.monotonic()"""
        else:
            # try connecting again?
            self.intellivue.close()
            self.intellivue.setup()
        # if connection failed, update what?

    def send_message(self):
        packet, err = self.intellivue.poll()
        responses = []
        if not err:
            print(packet)
            try:
                self.queue.put(
                    (
                        5,
                        Message(
                            topic=self.intellivue.vitals_topic,
                            payload=json.dumps(packet),
                        ),
                    )
                )
                # need to publish pulse here as well
            except:
                traceback.print_exc()
                responses.append["Couldnt publish vitals"]
            try:
                r = self.queue.put(
                    (
                        5,
                        Message(
                            topic=self.intellivue.legacy_vitals_topic,
                            payload=json.dumps(self.intellivue.legacy_vitals),
                        ),
                    )
                )
                responses.append(r)
            except:
                traceback.print_exc()
                responses.append["Couldnt publish legacy vitals"]
            try:
                pulse_topic, pulse_message = self.intellivue.pulse()
                self.queue.put((5, Message(topic=pulse_topic, payload=pulse_message)))
            except:
                traceback.print_exc()
                responses.append["Couldnt publish pulse"]
            # print(pulse_topic)
            return (
                self.intellivue.legacy_vitals,
                r,
            )  # self.client.publish(topic, json.dumps(packet))
        else:
            return self.intellivue.legacy_vitals, [-1]

    def report_status(self, msg, result, success_count, total_count):
        status = result[0]
        if status == 0:
            success_count += 1
            print(
                f"{success_count}/{total_count} Send at`{msg['v']}` to topic `{self.vitals_topic}`"
            )
        else:
            print(
                f"{total_count-success_count}/{total_count} Failed to send message to topic {self.vitals_topic}"
            )
        return success_count

    def _del(self):
        self.intellivue.close()
        self.logger.shutdown()

    def validate_hardware(self, starting_baud=115200):
        if self.intellivue.connected:
            return True
        elif self.intellivue.initial_connection_attempt + 60 < time.monotonic():
            self.status = "DISCONNECTED"
            self.intellivue.close()
            res = self.intellivue.setup()
            self.intellivue.close()
        else:
            return False
        return res


if __name__ == "__main__":
    q = queue.PriorityQueue(maxsize=3)
    x = parsers.parser.import_parsers()
    print(f"All parsers available: {x}")
    p = x["intellivue"].parser(tty="ttyAMA1", parent="123", txQueue=q)
    p.loop_start()
    last_status = None
    while True:
        if q.not_empty:
            print(f"\n\n\n\n\nRecieved {q.get()}\n\n\n\n\n")
        time.sleep(0.1)
        if last_status != p.intellivue.status:
            print("\n\n\n\n\n" + p.intellivue.status + "\n\n\n\n\n")
            last_status = p.intellivue.status

    # view longest delays between packets with
    # grep success mqtt_log.txt | cut -f1 -d' ' | sort | gnuplot -p -e "plot '<cat' title 'packet delay'"
    # grep success mqtt_log.txt | cut -f1 -d' ' | sort | gnuplot -p -e "set title 'Intellivue packet delay'; set ylabel 'delay'; set xlabel 'index'; plot '<cat' title 'packet delay'"
    # grep success mqtt_log.txt | cut -f1 -d' ' | sort | tail -n 10
