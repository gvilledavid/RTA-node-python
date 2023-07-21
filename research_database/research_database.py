import datetime
import random
import time
import paho.mqtt.client as mqtt
import ssl
import json
import traceback
import os
from TestData import physDict, settDict, vitDict, csvFiles, csvHeaders
import re
import queue
import subprocess
import signal
import sys
import pandas as pd

currDict, csvFile, csvHeader = None, None, None


class MQTT:
    def __init__(self, brokerName):
        # status and flag stuff
        self.is_connected = False
        self.was_connected = False
        self.UID = "test"  # get_mac("eth0")
        self.status = "DISCONNECTED"
        self.running = False
        self.writing = False

        # topic stuff
        self.status_topic = "Devices/status"
        self.subscription_topics = [("Devices/#", 1)]

        # queues
        self.commandQueue = queue.PriorityQueue()
        self.messageQueue = queue.PriorityQueue()

        # Authentication
        self.secrets = get_secrets(brokerName)
        self.client = self.connect_mqtt()

    def connect_mqtt(self):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:  # connected successfully
                for topic in self.subscription_topics:
                    client.subscribe(topic)
                if self.was_connected:
                    self.status = "RECONNECTED"
                    self.running = True
                    print(f"Recnnected to MQTT Broker {self.secrets.broker}!")
                else:
                    self.status = "CONNECTED"
                    self.running = True
                    print(f"Connected to MQTT Broker {self.secrets.broker}!")
                self.was_connected = True

            else:
                print("Failed to connect, return code %d\n", rc)
            print(userdata, flags, rc)  # None {'session present': 0} 0 on good
            self.is_connected = True

        def on_message(client, userdata, message):
            self.writing = True
            if self.running:
                print(f"Recieved {message.topic}")
                _, category, uid = message.topic.split("/")
                # save uid in parser
                # print(message.payload)
                global currDict, csvFile, csvHeader
                try:
                    data = json.loads(message.payload)
                    currDict, csvFile, csvHeader = find_type(category)
                    temp_dict = get_headers()
                except:
                    self.writing = False
                    return
                # print(data)
                data_UID = data.get("UID", None)
                data_Timestamp = data.get("timestamp", None)
                if not data_UID:
                    data["UID"] = uid
                if not data_Timestamp:
                    data["timestamp"] = str(int(time.time() * 1000))
                json_to_csv(data, temp_dict)
            self.writing = False

        def on_disconnect(client, two, three):
            print("Disconnected")
            self.is_connected = False
            self.running = False

        def on_connect_fail(client, userdata):
            print("failed to connect")
            self.is_connected = False
            self.running = False

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
        # client.will_set(self.pulse_topic,"Disconnected, will sent",qos=1,retain=True)
        client.connect(self.secrets.address, self.secrets.port)
        print(self.secrets.address, self.secrets.port)
        client.loop_start()
        while not self.is_connected:
            pass
        # client.subscribe(self.message_topic, 1)
        # client.message_callback_add(f"Devices/commands/{self.UID}", self.command_callback)
        # client.subscribe(self.command_topic, 1)
        for topic in self.subscription_topics:
            client.subscribe(topic)
        return client

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


class get_secrets:
    # store secrets in secrets_folder="/usr/local/share/.secrets/"
    #   broker/
    #       address.txt =address:port
    #       cert.pem
    #       private.pem
    #       CA.pem
    def __init__(self, broker):
        root_dir = os.path.abspath("/usr/local/share/.secrets/")
        self.broker = broker
        print(f"using {root_dir}")
        try:
            with open(os.path.join(root_dir, broker, "address.txt"), "r") as f:
                self.address, port = f.readline().replace("\n", "").split(":")
                self.port = int(port)
                if not self.port:
                    self.port = 1883  # default mqtt port
                if not self.address:
                    raise Exception("Address not specified in address.txt")
                self.username = f.readline().replace(
                    "\n", ""
                )  # returns empty line if nothing there
                self.password = f.readline().replace("\n", "")
        except:
            print(
                f"address.txt for {self.broker} does not exist or is not formatted correctly."
            )
        self.cert_file = os.path.join(root_dir, broker, "cert.pem")
        self.key_file = os.path.join(root_dir, broker, "private.pem")
        self.CA_file = os.path.join(root_dir, broker, "CA.pem")
        self.using_CA = os.path.isfile(self.CA_file)
        print(self.cert_file, self.key_file)
        self.cert = self.parse_pem(self.cert_file)
        self.key = self.parse_pem(self.key_file)
        if self.using_CA:
            self.CA = self.parse_pem(self.CA_file)

    def parse_pem(self, file):
        if not os.path.isfile(file):
            raise Exception(f"{file} does not exist")
        try:
            with open(file, "r") as f:
                x = f.read()
                x = re.sub("^[-]{5}.*[-]*$", "", x, flags=re.MULTILINE).replace(
                    "\n", ""
                )
            return x
        except:
            print(f"Could not open and parse{file}")
            return ""


def get_mac(interface_name):
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

    try:
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
    except:
        interface = (
            b"Ethernet adapter Ethernet"
            if interface_name == "eth0"
            else b"Wireless LAN adapter Wi-Fi"
        )
        print(
            "Linux    mac not found (is ip or iproute2 installed?) Trying windows mac."
        )
        x = subprocess.check_output("ipconfig /all", shell=True)
        first_eth_interface = x[x.find(interface) :]
        mac = first_eth_interface[first_eth_interface.find(b"Physical Address") :]
        mac = str(mac[mac.find(b":") : mac.find(b"\r")])[4:-1].replace("-", ":")
        return mac.lower()


def json_to_csv(json_data, template_dict):
    # json_data = json_data.replace("}{", "}}{{")
    # data = json_data.split("}{")
    template_dict = check_temp(json_data, template_dict)
    i = json_data["UID"]
    template_dict = dict_merge(json_data, clear_dict(template_dict))
    df = pd.DataFrame(template_dict, index=[None])
    make_csv(df)


def make_csv(df):
    with open(csvFile, "a") as f:
        df.to_csv(f, header=False, index=False, lineterminator="\n")
    df.loc[:, :] = " "
    try:
        dfr = pd.read_csv(csvHeader)
        dict1 = df.to_dict(orient="dict")
        dict2 = dfr.to_dict(orient="dict")
        if len(dict1) != len(dict2):
            df.to_csv(csvHeader, mode="w", header=True, index=False)
    except:
        df.to_csv(csvHeader, mode="w", header=True, index=False)


def dict_merge(dict1, dict2):
    new_dict = dict2
    new_dict.update(dict1)
    return new_dict


def check_temp(data, template_dict):
    template_dict.update(data)
    return clear_dict(template_dict)


def clear_dict(template_data):
    for i in template_data:
        template_data[i] = ""
    return template_data


# change header to only update on new key
def get_headers():
    try:
        df = pd.read_csv(csvHeader)
        dict = df.to_dict(orient="dict")
    except:
        dict = currDict
    return dict


def find_type(type):
    match type:
        case "phys":
            return (
                physDict,
                csvFiles["physFile"] + str(datetime.datetime.now().date()) + ".csv",
                csvHeaders["physHeader"],
            )
        case "settings":
            return (
                settDict,
                csvFiles["settFile"] + str(datetime.datetime.now().date()) + ".csv",
                csvHeaders["settHeader"],
            )
        case "vitals":
            return (
                vitDict,
                csvFiles["vitFile"] + str(datetime.datetime.now().date()) + ".csv",
                csvHeaders["vitHeader"],
            )
        case _:
            print("Error: Incorrect data type")
            raise Exception


if __name__ == "__main__":
    # azure = MQTT(get_secrets("Azure"))
    # aws = MQTT(get_secrets("AWS"))
    mac_address = "123"
    broker = MQTT("AWS")

    def term_proccess(signal_num, frame):
        broker.running = False
        while broker.writing:
            pass
        broker.disconnect()
        sys.exit()

    signal.signal(signal.SIGTERM, term_proccess)
    signal.signal(signal.SIGINT, term_proccess)

    try:
        while True:
            pass
    except:
        broker.running = False
        while broker.writing:
            pass
        broker.disconnect()

    # azure.sleep_time=1
    # node=pulse()
    # node.update()

    # currDict, csvFile, csvHeader = find_type(type)
    # for x in data:
    # json_to_csv(str(x), temp_dict, index)
    # json_to_csv(
    #   """{"UID": "1", "NOM_ECG_V_P_C_CNT": 0, "NOM_ECG_TIME_PD_QT_GL": 336, "NOM_ECG_TIME_PD_QTc": 442, "NOM_ECG_TIME_PD_QTc_DELTA": -11, "NOM_ECG_TIME_PD_QT_HEART_RATE": 104}{"UID": "1", "BP_SYS": 111, "BP_DIA": 55, "BP": 70, "F0E5": 102}{"UID": "1", "SPO2": 100.0, "4822": 103, "4BB0": 0.13, "HR": 104, "RR": 27, "NOM_ECG_AMPL_ST_I": 0.2, "NOM_ECG_AMPL_ST_II": 0.5, "NOM_ECG_AMPL_ST_AVF": 0.4}{"UID" : "2", "NOM_ECG_V_P_C_CNT": 0, "NOM_ECG_TIME_PD_QT_GL": 336, "NOM_ECG_TIME_PD_QTc": 442, "NOM_ECG_TIME_PD_QTc_DELTA": -11, "NOM_ECG_TIME_PD_QT_HEART_RATE": 104}{"UID" : "2", "BP_SYS": 111, "BP_DIA": 55, "BP": 70, "F0E5": 102}{"UID" : "2", "SPO2": 100.0, "4822": 103, "4BB0": 0.13, "HR": 104, "RR": 27, "NOM_ECG_AMPL_ST_I": 0.2, "NOM_ECG_AMPL_ST_II": 0.5, "NOM_ECG_AMPL_ST_AVF": 0.4}{"UID" :  "1", "NOM_ECG_V_P_C_CNT": 0, "NOM_ECG_TIME_PD_QT_GL": 336, "NOM_ECG_TIME_PD_QTc": 442, "NOM_ECG_TIME_PD_QTc_DELTA": -11, "NOM_ECG_TIME_PD_QT_HEART_RATE": 104}{"UID" :  "1", "BP_SYS": 111, "BP_DIA": 55, "BP": 70, "F0E5": 102}{"UID" :  "1", "SPO2": 100.0, "4822": 103, "4BB0": 0.13, "HR": 104, "RR": 27, "NOM_ECG_AMPL_ST_I": 0.2, "NOM_ECG_AMPL_ST_II": 0.5, "NOM_ECG_AMPL_ST_AVF": 0.4}{"UID" : "2", "BP_SYS": 111, "BP_DIA": 55, "BP": 70, "F0E5": 102}{"UID" :  "2", "NOM_ECG_V_P_C_CNT": 0, "NOM_ECG_TIME_PD_QT_GL": 336, "NOM_ECG_TIME_PD_QTc": 442, "NOM_ECG_TIME_PD_QTc_DELTA": -11, "NOM_ECG_TIME_PD_QT_HEART_RATE": 104}{"UID" : "2", "SPO2": 100.0, "4822": 103, "4BB0": 0.13, "HR": 104, "RR": 27, "NOM_ECG_AMPL_ST_I": 0.2, "NOM_ECG_AMPL_ST_II": 0.5, "NOM_ECG_AMPL_ST_AVF": 0.4}{"UID" :  "2", "NOM_ECG_V_P_C_CNT": 1000, "NOM_ECG_TIME_PD_QT_GL": 336, "NOM_ECG_TIME_PD_QTc": 442, "NOM_ECG_TIME_PD_QTc_DELTA": -11, "NOM_ECG_TIME_PD_QT_HEART_RATE": 104}{"UID" : "2", "BP_SYS": 111, "BP_DIA": 55, "BP": 70, "F0E5": 102}{"UID" : "2", "SPO2": 100.0, "4822": 103, "4BB0": 0.13, "HR": 104, "RR": 27, "NOM_ECG_AMPL_ST_I": 0.2, "NOM_ECG_AMPL_ST_II": 0.5,"Fakedata": 0.444, "NOM_ECG_AMPL_ST_AVF": 0.4}""",
    #  temp_dict)

# while not broker.is_connected:#wait until connect to publish
#     pass
# broker.publish("Pulse/leafs","Connected",qos=1,retain=True)
# while 1:
#   message = input("Type a message, or type \"EXIT\"")
#    if (message == "EXIT"):
#       break
#   else:
#        broker.publish("test/", message)
# broker.disconnect()
