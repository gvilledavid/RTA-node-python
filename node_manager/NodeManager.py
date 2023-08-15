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
import platform

# local includes
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger
from tools.get_secrets import get_secrets
from pulse.pulse import pulse, fake_windows_pulse
from tools.miamihosts import get_Miami_Hostname
from leaf_managers.leaf_manager import UARTLeafManager
from tools.MQTT import MQTT, Message, get_mac


class NodeManager:
    def __init__(self, brokerName):
        self.UID = get_mac("eth0")
        self.logger = RotatingLogger("NodeManager.log")
        self.leafs = {}
        for tty in self.detect_hardware():
            self.leafs[tty] = UARTLeafManager(tty, self.UID)
            self.leafs[tty].loop_start()

        # topic stuff
        self.qos = 1
        self.status_topic = f"Pulse/nodes/status/{self.UID}"
        self.command_topic = f"Devices/commands/{self.UID}"
        self.pulse_topic = f"Pulse/nodes/{self.UID}"
        self.subscription_topics = [
            (commands, self.qos)
            for commands in [self.leafs[leaf].command_topic for leaf in self.leafs]
        ]
        self.subscription_topics.append((self.command_topic, self.qos))
        if platform.system() == "Windows":
            self.pulse = fake_windows_pulse()
        else:
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
                b.add_to_mask("Pulse/#")
        self.pulse_freq = 60
        self.brief_freq = 10

        self.running = True
        self.main_loop()

    def __del__(self):
        for leaf in self.leafs:
            leaf.loop_stop()

        for b in self.brokers:
            b.shutdown()
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
                if self.pulse.dataready:
                    # pulse.pulse, pulse.pulse_topic to make a Message
                    msg = Message(payload=pulse.pulse, topic=pulse.pulse_topic)
                    for b in self.brokers:
                        b.put(priority, msg)
                    self.last_pulse = time.time()
                elif not self.pulse.updating:
                    self.pulse.update()
            elif time.time() - self.last_brief > self.brief_freq:
                if self.pulse.dataready:
                    msg = Message(payload=pulse.brief, topic=pulse.pulse_topic)
                    for b in self.brokers:
                        b.put(priority, msg)
                    self.last_brief = time.time()
                elif not self.pulse.updating:
                    self.pulse.brief_update()

            for leaf in self.leafs:
                if not self.leafs[leaf].is_alive():
                    pass
                    # why did it die? how to restart
                else:
                    while self.leafs[leaf].txQueue.qsize():
                        try:
                            priority, msg = self.leafs[leaf].txQueue.get()
                            # using msg.topic, decide if it is an action you can act on
                            print(msg)
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
    NodeManager(["Azure", "AWS", "cebabletier"])
