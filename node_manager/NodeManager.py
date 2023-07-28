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
from tools.MQTT import MQTT, MQTTMessage

class NodeManager:
    def __init__(self, brokerName):
        self.UID = get_mac("eth0")
        self.logger = RotatingLogger("NodeManager.log")
        self.leafs={}
        for tty in self.detect_hardware():
            self.leafs[tty]=UARTLeafManager(tty, tty,self.UID)
            self.leafs[tty].loop_start()
        
        # MQTT status and flag stuff
        self.is_connected = False
        self.was_connected = False
        self.status = "DISCONNECTED"

        # topic stuff
        self.status_topic = "Devices/status"
        self.command_topic = f"Devices/commands/{self.UID}"
        self.pulse_topic = f"Pulse/leafs/{self.UID}"
        self.message_topic = f"test/{self.UID}"
        self.subscription_topics = [
            (self.command_topic, 1),
            (self.pulse_topic, 1),
            (self.message_topic, 1),
        ]

        # queues
        self.commandQueue = queue.PriorityQueue()
        self.messageQueue = queue.PriorityQueue()

        # Authentication
        self.secrets = get_secrets(brokerName)
        self.client = self.connect_mqtt()
        #remove the above MQTT and instead use the MQTT library
        self.subscription_topics=[]
        self.qos=1
        self.subscription_topics.append((f"Commands/{self.UID}",self.qos))
        
        for leaf in self.leafs:
            self.subscription_topics.append((f"Commands/{self.UID}:{leaf}",self.qos))
        self.brokers=[]
        if type(brokerName) is str:
            self.brokers.append(MQTT(brokerName,self.subscription_topics))
        elif type(brokerName) is list:
            for b in brokerName:
                self.brokers.append(MQTT(b,self.subscription_topics))
        else:
            raise (f"brokerName must be a single broker or an array, not {type(brokerName)}")
        self.main_loop()
        
    def __del__(self):
        for leaf in self.leafs:
            leaf.stop_loop()
            self.disconnect()
            self.logger.shutdown()
            
    def detect_hardware(self):
        #todo load HW.conf for this version?
        try:
            ttyStatus = subprocess.check_output("ls /dev/piUART/status", shell=True)
            return str(ttyStatus)[2:-3].split("\\n")
        except:
            return ["ttyAMA1","ttyAMA2","ttyAMA3","ttyAMA4"]
    def process_commands(self):
        #send_pulse
        #restart: kill all leafs, call restart
        #set_time: should accept time, timezone, something like that
        #update: call apt update/upgrate
        #shutdown: rarely used but should be implimented
        #update certs:  pass certs and thumb and date valid
        #hostname update
        #req_id
        pass
    def main_loop(self):
        for leaf in self.leafs:
            if not leaf.is_alive():
                pass
                #why did it die? how to restart
            else:
                while self.qsize():
                    try:
                        priority, msg=self.get()
                        #using msg.topic, decide if it is an action you can act on
                        
        
    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:  # connected successfully
                for topic in self.subscription_topics:
                    client.subscribe(topic)
                if self.was_connected:
                    self.status = "RECONNECTED"
                    print(f"Recnnected to MQTT Broker {self.secrets.broker}!")
                else:
                    self.status = "CONNECTED"
                    print(f"Connected to MQTT Broker {self.secrets.broker}!")
                self.publish("Devices/status", "Connected")
                self.was_connected = True
                client.publish(self.pulse_topic, "Reconnected", qos=1, retain=True)

            else:
                print("Failed to connect, return code %d\n", rc)
            print(userdata, flags, rc)  # None {'session present': 0} 0 on good
            self.is_connected = True

        def on_message(client, userdata, message):
            print(f"Recieved {message.topic}")
            if message.topic == self.message_topic:
                self.message_callback(client, userdata, message)
            elif message.topic == self.command_topic:
                self.command_callback(client, userdata, message)

        def on_disconnect(client, two, three):
            print("Disconnected")
            self.is_connected = False

        def on_connect_fail(client, userdata):
            print("failed to connect")
            self.is_connected = False

        client = mqtt.Client()
        context = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH,
            cafile=(self.secrets.CA_file if self.secrets.using_CA else None),
        )  # self.secrets.using_CA ? self.secrets.CA_file : None
        print(self.secrets.CA_file, self.secrets.using_CA)
        context.load_cert_chain(
            certfile=self.secrets.cert_file,
            keyfile=self.secrets.key_file,
            password=None,
        )
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(context)

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_connect_fail = on_connect_fail
        client.on_disconnect = on_disconnect
        if self.secrets.username:
            client.username_pw_set(
                self.secrets.username,
                self.secrets.password if self.secrets.password else None,
            )
            # client.username_pw_set("ceadmin","Test32607")
            # print(f"|{self.secrets.username}|{self.secrets.password if self.secrets.password else None}|")
        client.will_set(self.pulse_topic, "Disconnected, will sent", qos=1, retain=True)
        client.connect(self.secrets.address, self.secrets.port)
        print(self.secrets.address, self.secrets.port)
        client.loop_start()
        while not self.is_connected:
            pass
        client.subscribe(self.message_topic, 1)
        # client.message_callback_add(f"Devices/commands/{self.UID}", self.command_callback)
        client.subscribe(self.command_topic, 1)
        return client

    def command_callback(self, client, userdata, message):
        print(
            f"Command {message.payload}, {message.topic=},{message.qos=},{message.retain=} "
        )

    def message_callback(self, client, userdata, message):
        print("message received ", str(message.payload))
        print("message topic=", message.topic)
        print("message qos=", message.qos)
        print("message retain flag=", message.retain)
        print(message)

    def publish(self, topic_root, data, qos=0, retain=False):
        # time.sleep(self.sleep_time)
        # total_count += 1
        topic = "".join([topic_root, "/", self.UID]).replace("//", "/")
        try:
            self.client.lastmsg = self.client.publish(
                topic, data, qos=qos, retain=retain
            )
        except:
            print("Unhandled exception in mqtt publish")

    def publishWithoutID(self, topic, dat, qoa=0, retain=False):
        try:
            self.client.lastmsg = self.client.publish(
                topic, data, qos=qos, retain=retain
            )
        except:
            print("Unhandled exception in mqtt publish")

    def disconnect(self):
        self.publish("Pulse/leafs/", "Disconnected,cleanly disconnected")
        self.client.lastmsg.wait_for_publish()
        self.client.loop_stop()
        self.client.disconnect()

    def register_leaf():
        pass


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
