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
            try:
                self.leafs[tty] = UARTLeafManager(tty, self.UID)
                self.leafs[tty].loop_start()
            except Exception as e:
                self.logger.critical(f"Failed to start LeafManager for {tty}: ")
        # topic stuff
        self.qos = 1
        self.priority = 5
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
            self.logger.critical(
                f"brokerName must be a single broker or an array, not {type(brokerName)}"
            )
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
            iter_time = time.monotonic()
            if time.monotonic() - self.last_pulse > self.pulse_freq:
                if self.pulse.dataready:
                    # pulse.pulse, pulse.pulse_topic to make a Message
                    for b in self.brokers:
                        if self.pulse.isdatavalid():
                            if b.name == "Azure":
                                b.put(
                                    self.priority,
                                    Message(
                                        topic=self.pulse.legacy_topic,
                                        payload=self.pulse.legacy_pulse,
                                    ),
                                )
                            else:
                                b.put(
                                    self.priority,
                                    Message(
                                        topic=self.pulse_topic, payload=self.pulse.pulse
                                    ),
                                )
                    self.last_pulse = time.monotonic()
                elif not self.pulse.updating:
                    self.pulse.update()
            elif time.monotonic() - self.last_brief > self.brief_freq:
                if self.pulse.dataready:
                    # pulse.pulse_brief, pulse.pulse_topic to make a Message
                    self.last_brief = time.monotonic()
                    if self.pulse.isdatavalid():
                        for b in self.brokers:
                            b.put(
                                self.priority,
                                Message(
                                    topic=self.pulse_topic, payload=self.pulse.brief
                                ),
                            )
                elif not self.pulse.updating:
                    self.pulse.brief_update()

            for leaf in self.leafs:
                if not self.leafs[leaf].is_alive():
                    pass
                    # TODO: check why it died and restart
                else:
                    while self.leafs[leaf].txQueue.not_empty:
                        try:
                            priority, msg = self.leafs[leaf].txQueue.get()
                            # using msg.topic, decide if it is an action you can act on
                            print(msg)
                            for b in self.brokers:
                                b.put(self.priority, msg)
                        except:
                            pass
            for b in self.brokers:
                while b.qsize():
                    val = b.get()
                    if val:
                        print(f"Recieved {val[1].payload} from {b.name}")
                        # if command for leaf, add to self.leafs[tty].rxQueue()
        time.sleep(0.1)


if __name__ == "__main__":
    NodeManager(["AWS"])
