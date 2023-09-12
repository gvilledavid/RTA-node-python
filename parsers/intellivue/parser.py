# Adapted from: https://www.emqx.com/en/blog/how-to-use-mqtt-in-python

import random
import time
import paho.mqtt.client as mqtt
import ssl
import json
import traceback
from intellivue.ivue import Intellivue
import subprocess
import serial, os, sys

# from parser folder
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
)  # add RTA-node-python to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path


import parsers.parser
from tools.MQTT import Message, MQTT


class parser(parsers.parser.parser):
    def _init(self):
        # scan baud rate here?
        self.name = "Intellivue"
        self.DID = ""
        self.vent_type = "MP70"
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
        self.intellivue = Intellivue(
            self.interface.split("/")[-1], self.serial_info["brate"], self.parent
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
        self._last_send = time.monotonic()
        # self.last_packet = {}

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
        self.publish()

    def send_message(self):
        packet, err = self.intellivue.poll()
        responses = []
        if not err:
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
                f"{success_count}/{total_count} Send at`{msg['v']}` to topic `{topic}`"
            )
        else:
            print(
                f"{total_count-success_count}/{total_count} Failed to send message to topic {topic}"
            )
        return success_count

    def publish(self, topic):
        success_count = 0
        total_count = 0

        total_count += 1
        try:
            if self._send_freq + self._last_send > time.monotonic():
                msg, result = self.send_message()
                self.check_deltas(msg)
                success_count = self.report_status(
                    msg, result, success_count, total_count
                )
                self._last_send = time.monotonic()
        except:
            print("Unhandled exception in mqtt publish, line 79")


if __name__ == "__main__":
    broker = "babletierdemo-beta.eastus.azurecontainer.io"
    port = 443
    cert_file = "../secrets/cert.pem"
    key_file = "../secrets/private.pem"
    topic = "Devices/pys/12:45:a3:bf:ed:12:ttyAMA3"
    server = MQTT(
        broker,
        port,
        cert_file,
        key_file,
        "Device/Vitals/e45f01db9e8dLeafMain1/e45f01db9e8d",
    )

    # view longest delays between packets with
    # grep success mqtt_log.txt | cut -f1 -d' ' | sort | gnuplot -p -e "plot '<cat' title 'packet delay'"
    # grep success mqtt_log.txt | cut -f1 -d' ' | sort | gnuplot -p -e "set title 'Intellivue packet delay'; set ylabel 'delay'; set xlabel 'index'; plot '<cat' title 'packet delay'"
    # grep success mqtt_log.txt | cut -f1 -d' ' | sort | tail -n 10
