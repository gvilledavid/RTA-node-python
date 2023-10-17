import paho.mqtt.client as mqtt

import random
import time
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

from leaf_managers.leaf_manager import LeafProcessorStates
from leaf_managers.leaf_manager import LeafProcessorCommands
from leaf_managers.leaf_manager import LeafProcessor
from pulse.pulse import pulse, fake_windows_pulse
from tools.RotatingLogger import RotatingLogger
from tools.get_secrets import get_secrets
from tools.miamihosts import get_Miami_Hostname
from tools.MQTT import MQTT, Message, get_mac


class NodeManager:
    def __init__(self, brokerName):
        self.UID = get_mac("eth0")
        self.logger = RotatingLogger("NodeManager.log")
        self.leafs = {}
        for connection_type, array_of_connections in self.detect_hardware().items():
            for connection in array_of_connections:
                try:
                    reference = f"{connection_type}_{connection}"
                    self.logger.critical(f"Starting LeafProcessor for {reference}.")
                    self.leafs[reference] = LeafProcessor(
                        connection_type, connection, self.UID
                    )
                except Exception as e:
                    self.logger.critical(
                        f"Failed to start LeafManager for {reference}: \n{e}"
                    )
        # topic stuff
        self.qos = 1
        self.priority = 5
        self.status_topic = f"Pulse/nodes/status/{self.UID}"
        self.command_topic = f"Devices/commands/{self.UID}"
        self.pulse_topic = f"Pulse/nodes/{self.UID}"
        self.subscription_topics = []
        # TODO: make the node store/generate the command topics and also store a list of what group
        # topics the leaf is connected to. Either a new command that goes through the pipe
        # or the node has to keep track of it. (and maybe store it to a file)
        """[    (commands, self.qos)
            for commands in [self.leafs[leaf].command_topic for leaf in self.leafs]
        ]"""
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
            leaf.join()
        # todo empty the queues and send?
        for b in self.brokers:
            b.shutdown()
        self.logger.shutdown()

    def detect_hardware(self):
        # todo load HW.conf for this version?
        # {"UART":[], "BT":[],etc}
        try:
            ttyStatus = subprocess.check_output("ls /dev/piUART/status", shell=True)
            return {"UART": str(ttyStatus)[2:-3].split("\\n")}
        except:
            return {"UART": ["ttyAMA1", "ttyAMA2", "ttyAMA3", "ttyAMA4"]}

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
        command_type = None
        leaf = None
        match command_type:
            case "t":
                packet = (5, Message(topic="", payload=""))
                leaf.transmit(packet)
            case "s":
                leaf.start()
            case "p":
                leaf.stop()
            case "e":
                leaf.echo()
            case "j":
                leaf.join()
            case "system_update":
                pass
            case "node_update":
                pass
            case "shutdown":
                pass
            case "restart":
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

            for key, leaf in self.leafs.items():
                if not leaf.proc_is_alive():
                    connection_type = leaf.connection_type
                    name = leaf.name
                    del self.leafs[key]
                    self.leafs[key] = LeafProcessor(connection_type, name, self.UID)
                elif not leaf.runner_is_alive():
                    leaf.start()
                else:
                    while not leaf.empty():
                        try:
                            priority, msg = leaf.recieve()
                            # TODO: using msg.topic, decide if it is an action you can act on
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
