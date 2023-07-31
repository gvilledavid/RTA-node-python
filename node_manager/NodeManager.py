import random
import time
import paho.mqtt.client as mqtt
import ssl
import json
import traceback
import os, sys
import re
import queue
import subprocess

# local includes
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger
from tools.get_secrets import get_secrets
from pulse.pulse import pulse, get_mac
from tools.miamihosts import get_Miami_Hostname
from leaf_managers.leaf_manager import UARTLeafManager
from tools.MQTT import MQTT, Message


class NodeManager:
    def __init__(self, brokerName):
        self.UID = get_mac("eth0")
        self.logger = RotatingLogger("NodeManager.log")
        self.leafs = {}
        for tty in self.detect_hardware():
            self.leafs[tty] = UARTLeafManager(tty, tty, self.UID)
            self.leafs[tty].loop_start()

        # topic stuff
        self.qos = 1
        self.status_topic = f"Pulse/nodes/status/{self.UID}"
        self.command_topic = f"Devices/commands/{self.UID}"
        self.pulse_topic = f"Pulse/nodes/{self.UID}"
        self.subscription_topics = [
            (commands, self.qos)
            for commands in [leaf.command_topic for leaf in self.leafs]
        ]
        self.subscription_topics.append((self.command_topic, self.qos))
        self.pulse = pulse()
        self.pulse.update()

        self.brokers = []
        if type(brokerName) is str:
            self.brokers.append(MQTT(brokerName, self.subscription_topics))
        elif type(brokerName) is list:
            for b in brokerName:
                self.brokers.append(MQTT(b, self.subscription_topics))

        else:
            raise (
                f"brokerName must be a single broker or an array, not {type(brokerName)}"
            )

        for b in self.brokers:
            while b.initialized and not b.is_connected:  # wait until connect to publish
                pass
            if b.name == "Azure":
                b.add_to_mask("Device/#")  # only publish to Device in Azure

        self.pulse_freq = 60
        self.brief_freq = 10

        self.main_loop()

    def __del__(self):
        for leaf in self.leafs:
            leaf.stop_loop()
            self.disconnect()
            self.logger.shutdown()
        self.brokers
        self.logger.shutdown()

    def detect_hardware(self):
        # todo load HW.conf for this version?
        try:
            ttyStatus = subprocess.check_output("ls /dev/piUART/status", shell=True)
            return str(ttyStatus)[2:-3].split("\\n")
        except:
            return ["ttyAMA1", "ttyAMA2", "ttyAMA3", "ttyAMA4"]

    def process_commands(self):
        # send_pulse
        # restart: kill all leafs, call restart
        # set_time: should accept time, timezone, something like that
        # update: call apt update/upgrate
        # shutdown: rarely used but should be implimented
        # update certs:  pass certs and thumb and date valid
        # hostname update
        # req_id
        pass

    def main_loop(self):
        self.last_pulse = 0
        self.last_brief = 0
        while self.running:
            iter_time = time.time()
            if time.time() - self.last_pulse > self.pulse_freq:
                pulse.update()
            elif time.time() - self.last_brief > self.brief_freq:
                pulse.brief_update()

            for leaf in self.leafs:
                if not leaf.is_alive():
                    pass
                    # why did it die? how to restart
                else:
                    while self.leaf.qsize():
                        try:
                            priority, msg = self.get()
                            # using msg.topic, decide if it is an action you can act on
                            for b in self.brokers:
                                b.put(priority, msg)
                        except:
                            pass
            for b in self.brokers:
                while b.qsize():
                    val = b.get()
                    if val:
                        print(f"Recieved {val[1].payload} from {b.name}")
                        # if command for leaf, add to self.leafs[tty].rxQueue()
            # check pulse, send if available


if __name__ == "__main__":
    # azure = MQTT(get_secrets("Azure"))
    # aws = MQTT(get_secrets("AWS"))
    mac_address = "123"
    broker = MQTT("Azure")
    # azure.sleep_time=1
    # node=pulse()
    # node.update()
    while not broker.is_connected:  # wait until connect to publish
        pass
    broker.publish("Pulse/leafs", "Connected", qos=1, retain=True)
    while 1:
        message = input('Type a message, or type "EXIT"')
        if message == "EXIT":
            break
        else:
            broker.publish("test/", message)
    broker.disconnect()
