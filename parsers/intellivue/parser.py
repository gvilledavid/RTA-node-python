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
from tools.MQTT import Message


class parser(parsers.parser.parser):
    def __init__(self):  # , broker, port, cert_file, key_file, topic):
        self.intellivue = Intellivue("ttyAMA3", 115200, get_mac("wlan0"))
        self.last_packet = {"last_time": time.time()}
        self.client = self.connect_mqtt(broker, port, cert_file, key_file)
        self.client.loop_start()
        self.publish(topic)
        self.topic = topic

    def connect_mqtt(self, broker, port, cert_file, key_file):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print("Failed to connect, return code %d\n", rc)

        client = mqtt.Client()
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=None)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file, password=None)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(context)

        client.on_connect = on_connect
        client.connect(broker, port)
        return client

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

    def send_message(self):
        packet, err = self.intellivue.poll()
        responses = []
        if not err:
            try:
                responses.append(
                    self.client.publish(
                        self.intellivue.vitals_topic, json.dumps(packet)
                    )
                )
                # need to publish pulse here as well
            except:
                traceback.print_exc()
                responses.append["Couldnt publish vitals"]
            try:
                r = self.client.publish(
                    self.intellivue.legacy_vitals_topic,
                    json.dumps(self.intellivue.legacy_vitals),
                )
                responses.append(r)
            except:
                traceback.print_exc()
                responses.append["Couldnt publish legacy vitals"]
            try:
                pulse_topic, pulse_message = self.intellivue.pulse()
                responses.append(self.client.publish(pulse_topic, pulse_message))
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

        while True:
            time.sleep(0.1)  # Send a message every ~1s
            total_count += 1
            try:
                msg, result = self.send_message()
                self.check_deltas(msg)
                success_count = self.report_status(
                    msg, result, success_count, total_count
                )
            except:
                print("Unhandled exception in mqtt publish, line 79")


def param_from_iface(iface_str, param):
    index = iface_str.find(param + " ")
    if index == -1:
        return ""
    start_index = index + len(param) + 1
    index = iface_str[start_index:].find(" ")
    if index != -1:
        return iface_str[start_index : start_index + index]
    else:
        return iface_str[start_index:]


def get_mac(interface_name):
    stdoutval = str(subprocess.check_output("ip address show", shell=True))[2:-1]
    list = []
    link = 1
    while len(stdoutval) > 3:
        end_index = stdoutval.find(f"\\n{link+1}")
        if end_index == -1:
            end_index = len(stdoutval)
        this_link = stdoutval[:end_index]
        list.append(this_link)
        stdoutval = stdoutval[end_index:].replace("\\n", "", 1)
        link += 1
    for link in list:
        if link[2 : link[2:].find(":") + 2].strip() == interface_name:
            return param_from_iface(link, "link/ether")


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
