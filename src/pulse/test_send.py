
import random
import time
import paho.mqtt.client as mqtt
import ssl
import json
import traceback
import os
import re


class MQTT:
    def __init__(self, secrets,UID):
        self.UID=UID
        self.last_packet = {"last_time": time.time()}
        self.secrets = secrets
        print(secrets.cert_file, secrets.key_file)
        self.client = self.connect_mqtt(
            secrets.address, secrets.port, secrets.cert_file, secrets.key_file)

        self.sleep_time = 5
    # todo: on_disconnect function
    # todo: subscribe to commands

    def connect_mqtt(self, broker, port, cert_file, key_file):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"Connected to MQTT Broker {self.secrets.broker}!")
            else:
                print("Failed to connect, return code %d\n", rc)

        def on_message(client, userdata, message):
            print("message received ", str(message.payload))
            print("message topic=", message.topic)
            print("message qos=", message.qos)
            print("message retain flag=", message.retain)

        def on_disconnect(client,two,three):
            print("Disconnected")

        def on_connect_fail(client, userdata):
            print("failed to connect")
        client = mqtt.Client()
        context = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH, cafile=None)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file, password=None)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(context)

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_connect_fail = on_connect_fail
        #client.message_callback_add(f"Devices/commands/{self.UID}", self.command_callback)
        client.on_disconnect = on_disconnect
        if(self.secrets.username):
            #client.username_pw_set(self.secrets.username, self.secrets.password if self.secrets.password else None)
            client.username_pw_set("ceadmin","Test32607")
            print(f"|{self.secrets.username}|{self.secrets.password if self.secrets.password else None}|")
        client.will_set(f"Pulse/leafs/{self.UID}","Disconnected, will sent",qos=1,retain=True)
        client.connect(broker, port)
        client.loop_start()
        client.subscribe(f"test/{self.UID}",1)
        client.subscribe(f"Devices/commands/{self.UID}",1)
        return client
    
    def command_callback(client, userdata, message):
        print(
            f"Command {message.payload}, {message.topic=},{message.qos=},{message.retain=} ")

    def publish(self, topic_root, data):
        # time.sleep(self.sleep_time)
        # total_count += 1
        topic="".join([topic_root,"/",self.UID]).replace("//","/")
        try:
            self.client.lastmsg = self.client.publish(topic, data)
        except:
            print("Unhandled exception in mqtt publish")

    def disconnect(self):
        self.client.lastmsg.wait_for_publish()
        self.client.loop_stop()
        self.client.disconnect()


class get_secrets():
    # store secrets in secrets_folder="/usr/local/share/.secrets/"
    #   broker/
    #       address.txt =address:port
    #       cert.pem
    #       private.pem
    #       CA.pem
    def __init__(self, broker):
        root_dir = os.path.abspath("/usr/local/share/.secrets/")
        self.broker = broker
        print(F"using {root_dir}")
        try:
            with open(os.path.join(root_dir, broker, "address.txt"), 'r') as f:
                self.address, port = f.readline().replace("\n", "").split(":")
                self.port = int(port)
                self.username=f.readline().replace("\n", "")
                self.password=f.readline().replace("\n", "")
                print(self.username)
                print(self.password)
        except:
            print(
                f"address.txt for {broker} does not exist or is not formatted correctly.")
        self.cert_file = os.path.join(root_dir, broker, "cert.pem")
        self.key_file = os.path.join(root_dir, broker, "private.pem")
        print(self.cert_file,self.key_file)
        self.cert = self.parse_pem(self.cert_file)
        self.key = self.parse_pem(self.key_file)

    def parse_pem(self, file):
        if(not os.path.isfile(file)):
            raise Exception(f"{file} does not exist")
        try:
            with open(file, 'r') as f:
                x = f.read()
                x = re.sub("^[-]{5}.*[-]*$", "", x,
                           flags=re.MULTILINE).replace("\n", "")
            return x
        except:
            print(f"Could not open and parse{file}")
            return ""


if __name__ == '__main__':
    # azure = MQTT(get_secrets("Azure"))
    # aws = MQTT(get_secrets("AWS"))
    miami = MQTT(get_secrets("cebabletier"),"123")
    # azure.sleep_time=1
    # node=pulse()
    # node.update()
    miami.publish("Pulse/leafs","Connected")
    while 1:
        message = input("Type a message, or type \"EXIT\"")
        if (message == "EXIT"):
            break
        else:
            miami.publish("test/", message)
    miami.disconnect()
