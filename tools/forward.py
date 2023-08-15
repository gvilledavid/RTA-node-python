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
from tools.MQTT import MQTT, Message


if __name__ == "__main__":
    sublist = [("Devices/#", 0)]
    Azure = MQTT("Azure")
    AWS = MQTT("AWS", sublist)
    map = {
        "e45f01a6e5ba": "e45f01a6e5bc",
        "dca6327042ee": "dca6327042ef",
        "dca632e93aab": "dca632e93aac",
        "e45f01a6e5ec": "e45f01a6e5ed",
        "e45f01a6e5fb": "e45f01a6e5fc",
        "e45f01a6e5e6": "e45f01a6e5e7",
        "e45f01db9f3b": "e45f01db9f3d",
        "e45f01a6e4be": "e45f01a6e4c1",
        "e45f01dbe54f": "e45f01dbe550",
        "e45f01dbce4c": "e45f01dbce4d",
        "e45f01dbe1e6": "e45f01dbe1ea",
        "e45f01db9e8c": "e45f01db9e8d",
        "e45f01dbe694": "e45f01dbe695",
        "e45f01dbe6be": "e45f01dbe6bf",
        "e45f01dbd84e": "e45f01dbd84f",
        "e45f01dbe682": "e45f01dbe684",
        "e45f0124fa33": "e45f0124fa35",
        "e45f0156abeb": "e45f0156abed",
        "e45f0124f98a": "e45f0124f98b",
        "e45f0125136d": "e45f0125136e",
        "e45f01247536": "e45f01247537",
        "e45f010e9c22": "e45f010e9c23",
        "e45f0147f737": "e45f0147f738",
        "e45f0124dfe0": "e45f0124dfe1",
        "e45f012454cc": "e45f012454cd",
        "e45f0124e001": "e45f0124e002",
    }
    while Azure.initialized and not Azure.is_connected:  # wait until connect to publish
        pass
    while AWS.initialized and not AWS.is_connected:  # wait until connect to publish
        pass
    # try:
    while 1:
        time.sleep(0.25)
        while AWS.qsize():
            msg = AWS.get()[1]
            if msg:
                # rename topic:
                # uid = ":".join(msg.topic.split("/")[-1].split(":")[0:-1])
                # new_uid = map.get(uid, uid.replace(":", "").lower())
                # msg.topic = msg.topic.replace(uid, new_uid)

                # rename topic
                uid = msg.topic.split("/")[-1].split(":")[:-1]
                uid = "".join(uid)
                uid = uid.replace(":", "").lower()
                new_uid = map.get(uid, None)
                msg.topic = f"Device/Vitals/{uid}LeafMain1/{uid}"
                try:
                    msg.payload = json.dumps(
                        {
                            "v": str(int(time.time() * 1000)),
                            "n": "v",
                            "l": [
                                {"n": name, "v": value}
                                for name, value in json.loads(msg.payload[2:-1]).items()
                            ],
                        }
                    )
                except:
                    print("error")
                    print(f"{msg.topic=}\n{msg.payload}")
                if new_uid:
                    msg.topic = msg.topic.replace(uid, new_uid)
                print(msg.topic)
                print(msg.payload)
                Azure.put(1, msg)
    # except:
    #    AWS.shutdown()
    #    Azure.shutdown()
