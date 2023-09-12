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
from threading import Lock

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)  # add RTA-node-python to path
from tools.RotatingLogger import RotatingLogger
from tools.get_secrets import get_secrets
from pulse.pulse import pulse, get_mac


# priority queue:
# 1: alarms, 3:pulse, 5:default, 6:vitals/phys, 7:settings
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

    def __init__(self, *args, **kwargs):
        """Pass a MQTTMessage or Message object to copy
        Otherwise use keywords from slots to populate a new Message
        """
        if len(args) == 1 and isinstance(args[0], (Message, MQTTMessage)):
            if isinstance(args[0], MQTTMessage):
                self.timestamp = str(
                    int(1000 * time.time())
                )  # overwrite paho  monotonic time
            else:
                self.timestamp = args[0].timestamp
            self.state = args[0].state
            self.dup = args[0].dup
            self.mid = args[0].mid
            self._topic = args[0]._topic
            self.payload = args[0].payload
            if isinstance(self.payload, dict):
                self.payload = json.dumps(self.payload)
            else:
                self.payload = str(self.payload)
            self.qos = args[0].qos
            self.retain = args[0].retain
        elif len(args) > 0:
            raise SyntaxError(
                "Non Message or MQTTMessage positional argument given. Did you forget keywords?"
            )
        else:
            self.timestamp = kwargs.get("timestamp", str(int(1000 * time.time())))
            self.state = kwargs.get("state", mqtt.mqtt_ms_invalid)
            self.dup = kwargs.get("dup", False)
            self.mid = kwargs.get("mid", 0)
            self._topic = kwargs.get("topic", b"")
            self.payload = kwargs.get("payload", b"")
            self.qos = kwargs.get("qos", 0)
            self.retain = kwargs.get("retain", False)

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
        if type(self._topic) == bytes:
            return self._topic.decode("utf-8")
        return self._topic

    @topic.setter
    def topic(self, value):
        self._topic = value

    def dict(self):
        return json.loads(self.payload)

    def topic_child(self):
        return self.subtopics()[-1]

    def subtopics(self):
        return self.topic.split("/")

    def __repr__(self) -> str:
        return f"{self.__class__}:\n\t{self.topic=}\n\t{self.qos=} {self.retain=}\n\t{self.payload=}"


class MQTT:
    def __init__(self, brokerName, sublist=[], logger=None, pub_mask=None):
        if not logger:
            self.logger = RotatingLogger(f"{brokerName}-MQTT.log")
        else:
            self.logger = logger
        # status and flag stuff
        self.initialized = False
        self.is_connected = False
        self.was_connected = False
        self.UID = get_mac("eth0")
        self.status = "DISCONNECTED"
        self.name = brokerName
        # topic stuff
        self.subscription_topics = sublist
        self.status_topic = f"Pulse/nodes/status/{self.UID}"
        # queues
        # These queues define the MQTt-Node connection from this library's point of view
        #   tx is the transmit to node queue, it is for recieved broker messages that are forwarded to the Node
        #   rx is for messages recieved from the Node, which will be published to the broker
        self.txQueue = queue.PriorityQueue(maxsize=1000)
        self.rxQueue = queue.PriorityQueue(maxsize=1000)

        # publisher thread
        self.publisher = threading.Thread(target=self.publish_handler, args=())
        self.pub_running = False
        self.pub_stopped = True
        self.get_lock = Lock()
        self.put_lock = Lock()
        self.mask = pub_mask

        # Authentication
        self.secrets = get_secrets(brokerName)
        self.client = self.connect_mqtt()

    def add_to_mask(self, topic):
        # TODO: verify topic is well-formed?
        if not self.mask:
            self.mask = []
        if type(topic) == list:
            self.mask.extend(topic)
        else:
            self.mask.append(topic)

    def publish_mask(self, topic):
        if not self.mask:
            return True
        for t in self.mask:
            if mqtt.topic_matches_sub(t, topic):
                return True
        return False

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:  # connected successfully
                if client.parent.subscription_topics:
                    for topic in client.parent.subscription_topics:
                        client.subscribe(topic)
                if client.parent.was_connected:
                    client.parent.status = "RECONNECTED"
                    client.parent.logger.info(
                        f"Reconnected to MQTT Broker {client.parent.secrets.broker}!"
                    )
                else:
                    client.parent.status = "CONNECTED"
                    client.parent.logger.info(
                        f"Connected to MQTT Broker {client.parent.secrets.broker}!"
                    )
                client.parent.was_connected = True
                client.publish(
                    client.parent.status_topic,
                    "{"
                    + f'"status":"Connected","message":"{client.parent.status}"'
                    + "}",
                    qos=1,
                    retain=True,
                )
                if not client.parent.publisher_running():
                    client.parent.publisher_start()

            else:
                client.parent.logger.info(f"Failed to connect, return code {rc}\n")
                client.parent.publisher_stop()
            client.parent.logger.info(str([userdata, flags, rc]))
            # None {'session present': 0} 0 on good
            client.parent.is_connected = True

        def on_message(client, userdata, message):
            client.parent.logger.info(f"Recieved from broker: {message.topic}")
            if not client.parent.txQueue.full():
                try:
                    client.parent.txQueue.put_nowait((5, Message(message)))
                except queue.Full:
                    client.parent.logger.critical(
                        "tx queue is full and this message is lost."
                    )
                except:
                    client.parent.logger.critical(
                        "unknown exception when writing to tx queue. Message is lost."
                    )
            else:
                client.parent.logger.critical(
                    "tx queue is full and this message is lost."
                )

        def on_disconnect(client, two, three):
            client.parent.publisher_stop()
            client.parent.logger.info("Disconnected")
            client.parent.is_connected = False

        def on_connect_fail(client, userdata):
            client.parent.publisher_stop()
            client.parent.logger.info("failed to connect")
            client.parent.is_connected = False

        client = mqtt.Client()
        client.parent = self
        self.client = client
        context = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH,
            cafile=(self.secrets.CA_file if self.secrets.using_CA else None),
        )  # self.secrets.using_CA ? self.secrets.CA_file : None
        self.logger.info(str([self.secrets.CA_file, self.secrets.using_CA]))
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
        client.lastmsg = None
        if self.secrets.username:
            client.username_pw_set(
                self.secrets.username,
                self.secrets.password if self.secrets.password else None,
            )
            # client.username_pw_set("ceadmin","Test32607")
            # print(f"|{self.secrets.username}|{self.secrets.password if self.secrets.password else None}|")
        client.will_set(
            self.status_topic,
            "{"
            + f'"status":"Disconnected","message":"Uncleanly disconnected, lwt sent"'
            + "}",
            qos=1,
            retain=True,
        )
        self.logger.info(str([self.secrets.address, self.secrets.port]))
        ret_err = 1
        try:
            ret_err = client.connect(self.secrets.address, self.secrets.port)
            if not ret_err:
                client.loop_start()
            end_time = 10 + time.time()
            while not self.is_connected:
                if time.time() > end_time:
                    raise TimeoutError
            self.initialized = True
        except TimeoutError:
            self.logger.critical(f"Server could not be reached at hostname")
        except:
            self.logger.critical(f"Could not connect")

        return client

    def publish(self, topic_root, data, qos=0, retain=False):
        if not self.initialized or not self.is_connected:
            return
        # time.sleep(self.sleep_time)
        # total_count += 1
        topic = "".join([topic_root, "/", self.UID]).replace("//", "/")
        try:
            self.client.lastmsg = self.client.publish(
                topic, data, qos=qos, retain=retain
            )
        except:
            self.logger.info("Unhandled exception in mqtt publish")

    def publishWithoutID(self, msg):
        if not self.initialized or not self.is_connected:
            return
        try:
            self.client.lastmsg = self.client.publish(
                msg.topic, msg.payload, qos=msg.qos, retain=msg.retain
            )
        except:
            self.logger.info("Unhandled exception in mqtt publish")

    def shutdown(self):
        self.publishWithoutID(
            Message(
                topic=self.status_topic,
                payload="{"
                + f'"status":"Disconnected","message":"Cleanly disconnected"'
                + "}",
                qos=1,
                retain=True,
            )
        )
        if self.client.lastmsg:
            self.client.lastmsg.wait_for_publish()
        self.publisher_stop(10)
        self.client.disconnect()
        self.client.loop_stop()
        self.logger.shutdown()

    def publish_handler(self):
        while self.pub_running:
            try:
                while self.rxQueue.qsize():
                    priority, msg = self.rxQueue.get()
                    if self.publish_mask(msg.topic):
                        self.publishWithoutID(msg)
            except queue.Empty:
                pass  # todo, something here
            except:
                pass  # todo, something here
            time.sleep(0.05)
        self.pub_stopped = True
        self.pub_running = False

    def publisher_start(self):
        self.pub_running = True
        self.pub_stopped = False
        self.publisher.start()

    def publisher_stop(self, time_out=1):
        self.pub_running = False
        st = time.time()
        while self.publisher_running() or self.publisher.is_alive():
            if time_out and st + time_out > time.time():
                break
            self.publisher.join(timeout=0.01)

    def publisher_running(self):
        return not self.pub_stopped

    def get(self):
        # wrapper for txqueue.get
        if self.initialized:
            with self.get_lock:
                if self.txQueue.qsize():
                    try:
                        return self.txQueue.get_nowait()
                    except queue.Empty:
                        self.logger.info("txqueue empty, not returning anything.")
                    except:
                        self.logger.critical("Unhandled exception in MQTT.get")
        return (10, None)

    def qsize(self):
        return self.txQueue.qsize()

    def qempty(self):
        return self.txQueue.empty()

    def qfull(self):
        return self.rxQueue.full()

    def put(self, priority, msg, nolog=False):
        # wrapper for rxqueue.put
        if self.initialized:
            with self.put_lock:
                if not self.qfull():
                    try:
                        self.rxQueue.put_nowait((priority, msg))
                        return True
                    except queue.Empty:
                        if not nolog:
                            self.logger.info("txqueue empty, not returning anything.")
                    except:
                        if not nolog:
                            self.logger.critical("Unhandled exception in MQTT.get")
                else:  # when full, throw away the lowest priority thing
                    self.rxQueue.queue.pop()
        return False

    def put_blocking(self, priority, msg, timeout=0):
        if (not type(timeout) == int) or timeout < 0:
            timeout = 0
        end_time = time.time() + timeout
        self.logger.info(f"put_blocking starting with {timeout=}")
        ret = self.put(priority, msg)
        while not ret and (timeout == 0 or time.time() <= end_time):
            ret = self.put(priority, msg, nolog=True)
        self.logger.info(
            f"put_blocking finished in {time.time()-end_time+timeout} seconds, published: {ret}"
        )
        return ret


if __name__ == "__main__":
    sublist = [("test2/#", 0), ("test4", 0)]
    brokers = [
        MQTT("Azure", sublist),
        MQTT("AWS", sublist),
        MQTT("cebabletier", sublist),
    ]
    brokers[0].add_to_mask("test")
    brokers[1].add_to_mask("test3")
    for b in brokers:
        while b.initialized and not b.is_connected:  # wait until connect to publish
            pass
        b.put(
            5,
            Message(
                topic=f"Pulse/nodes/{b.UID}", payload="Connected", qos=1, retain=True
            ),
        )
        # can use b.qfull(), and also check the return value to see if it passed
        # b.put_blocking( priority, msg, timeout=0) to force it to wait timeout if timout is a pos int, or forever otherwise
    while 1:
        message = input('Type a message, or type "EXIT"')
        if message == "EXIT":
            for b in brokers:
                b.shutdown()
            break
        else:
            m = Message(payload=message, topic="test")
            m2 = Message(payload=message, topic="test3")
            for b in brokers:
                b.put(1, m)
                b.put(1, m2)
        for b in brokers:
            while b.qsize():
                val = b.get()
                # (priority, Message) tuple. check if Message is True before using
                if val:
                    print(f"Recieved {val[1].payload} from {b.name}")
