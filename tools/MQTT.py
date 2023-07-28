import random
import time
import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessage
import ssl
import json
import traceback
import os, sys
import re
import queue
import subprocess
import json
import threading

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger
from tools.get_secrets import get_secrets
from pulse.pulse import pulse, get_mac


class Message(MQTTMessage):
    """
    topic : String. topic that the message was published on.
    payload : Bytes/Byte array. the message payload.
    qos : Integer. The message Quality of Service 0, 1 or 2.
    retain : Boolean. If true, the message is a retained message and not fresh.
    properties: Properties class. In MQTT v5.0, the properties associated with the message.
    """

    __slots__ = (
        "timestamp",
        "state",
        "dup",
        "mid",
        "_topic",
        "payload",
        "qos",
        "retain",
        "properties",
    )

    def __init__(self, mid=0, topic=b"", payload=b"", qos=0, retain=False):
        self.timestamp = int(time.time() * 1000)
        self.dup = False
        self.mid = mid
        self._topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.mid == other.mid
        return False

    def __ne__(self, other):
        """Define a non-equality test"""
        return not self.__eq__(other)

    @property
    def topic(self):
        return self._topic.decode("utf-8")

    @topic.setter
    def topic(self, value):
        self._topic = value

    def dict(self):
        return json.loads(self.payload)

    def topic_child(self):
        return self.subtopics()[-1]

    def subtopics(self):
        return self.topic.split("/")


class MQTT:
    def __init__(self, brokerName, sublist, logger=None):
        if not logger:
            self.logger = RotatingLogger(f"{brokerName}-MQTT.log")
        else:
            self.logger = logger
        # status and flag stuff
        self.is_connected = False
        self.was_connected = False
        self.UID = get_mac("eth0")
        self.status = "DISCONNECTED"

        # topic stuff
        self.subscription_topics = sublist
        self.status_topic = "Pulse/nodes/status"
        # queues
        # These queues define the MQTt-Node connection from this library's point of view
        #   tx is the transmit to node queue, it is for recieved broker messages that are forwarded to the Node
        #   rx is for messages recieved from the Node, which will be published to the broker
        self.txQueue = queue.PriorityQueue()
        self.rxQueue = queue.PriorityQueue()

        # Authentication
        self.secrets = get_secrets(brokerName)
        self.client = self.connect_mqtt()
        # publisher thread
        self.publisher = threading.Thread(target=self.publish_handler, args=())
        self.pub_running = False
        self.pub_stopped = True

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:  # connected successfully
                for topic in self.subscription_topics:
                    client.subscribe(topic)
                if self.was_connected:
                    self.status = "RECONNECTED"
                    self.logger.info(
                        f"Reconnected to MQTT Broker {self.secrets.broker}!"
                    )
                else:
                    self.status = "CONNECTED"
                    self.logger.info(f"Connected to MQTT Broker {self.secrets.broker}!")
                self.was_connected = True
                client.publish(self.status_topic, "Connected", qos=1, retain=True)

            else:
                self.logger.info("Failed to connect, return code %d\n", rc)
            self.logger.info(
                userdata, flags, rc
            )  # None {'session present': 0} 0 on good
            self.is_connected = True

        def on_message(client, userdata, message):
            self.logger.info(f"Recieved {message.topic}")
            self.txQueue.put((5, message))

        def on_disconnect(client, two, three):
            self.logger.info("Disconnected")
            self.is_connected = False

        def on_connect_fail(client, userdata):
            self.logger.info("failed to connect")
            self.is_connected = False

        client = mqtt.Client()
        context = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH,
            cafile=(self.secrets.CA_file if self.secrets.using_CA else None),
        )  # self.secrets.using_CA ? self.secrets.CA_file : None
        self.logger.info(self.secrets.CA_file, self.secrets.using_CA)
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
        self.logger.info(self.secrets.address, self.secrets.port)
        client.loop_start()
        while not self.is_connected:
            pass
        client.subscribe(self.message_topic, 1)
        # client.message_callback_add(f"Devices/commands/{self.UID}", self.command_callback)
        client.subscribe(self.command_topic, 1)
        return client

    def publish(self, topic_root, data, qos=0, retain=False):
        # time.sleep(self.sleep_time)
        # total_count += 1
        topic = "".join([topic_root, "/", self.UID]).replace("//", "/")
        try:
            self.client.lastmsg = self.client.publish(
                topic, data, qos=qos, retain=retain
            )
        except:
            self.logger.info("Unhandled exception in mqtt publish")

    def publishWithoutID(self, topic, data, qos=0, retain=False):
        try:
            self.client.lastmsg = self.client.publish(
                topic, data, qos=qos, retain=retain
            )
        except:
            self.logger.info("Unhandled exception in mqtt publish")

    def disconnect(self):
        self.publish(self.status_topic, "Disconnected:cleanly disconnected")
        self.client.lastmsg.wait_for_publish()
        self.client.loop_stop()
        self.client.disconnect()

    def publish_handler(self):
        while self.pub_running:
            try:
                while self.rxQueue.qsize():
                    msg = self.rxQueue.get()
                    self.publishWithoutID(msg.topic, msg.data, msg.qos.msg.retain)
            except:
                pass
        self.pub_stopped = True
        self.pub_running = False

    def publisher_start(self):
        self.pub_running = True
        self.pub_stopped = False
        self.publisher.start()

    def publisher_stop(self):
        self.pub_running = False
        ct = 0
        tmMAX = 10
        while self.publisher_running() or self.publisher.is_alive():
            ct += ct
            if ct > tmMAX:
                break
            self.publisher.join(timeout=0.01)

    def publisher_running(self):
        return not self.pub_stopped


if __name__ == "__main__":
    sublist = [("Devices/#", 0)]
    brokers = [MQTT("Azure", sublist), MQTT("AWS", sublist), MQTT("Azure", sublist)]

    for b in brokers:
        while not b.is_connected:  # wait until connect to publish
            pass
        b.rxqueue(f"Pulse/leafs/{b.UID}", "Connected", qos=1, retain=True)
    while 1:
        message = input('Type a message, or type "EXIT"')
        if message == "EXIT":
            break
        else:
            for b in brokers:
                b.publish("test/", message)
    for b in brokers:
        b.disconnect()
