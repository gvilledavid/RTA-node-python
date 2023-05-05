
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
        self.is_connected=False
        self.was_connected=0
        self.UID=UID
        self.command_topic=f"Devices/commands/{self.UID}"
        self.pulse_topic=f"Pulse/leafs/{self.UID}"
        self.message_topic=f"test/{self.UID}"
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
            if rc == 0 and not self.was_connected:
                print(f"Connected to MQTT Broker {self.secrets.broker}!")
                self.was_connected=1
            elif rc == 0 :
                print("Reconnected")
                miami.publish("Pulse/leafs","Reconnected",qos=1,retain=True)
            else:
                print("Failed to connect, return code %d\n", rc)
            print( userdata,flags,rc) #None {'session present': 0} 0 on good
            self.is_connected=True
        def on_message(client, userdata, message):
            print(f"Recieved {message.topic}")
            if(message.topic==self.message_topic):
                self.message_callback(client, userdata, message)
            elif(message.topic==self.command_topic):
                self.command_callback(client, userdata, message)

        def on_disconnect(client,two,three):
            print("Disconnected")
            self.is_connected=False
        def on_connect_fail(client, userdata):
            print("failed to connect")
            self.is_connected=False
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
        client.on_disconnect = on_disconnect
        if(self.secrets.username):
            client.username_pw_set(self.secrets.username, self.secrets.password if self.secrets.password else None)
            #client.username_pw_set("ceadmin","Test32607")
            #print(f"|{self.secrets.username}|{self.secrets.password if self.secrets.password else None}|")
        client.will_set(self.pulse_topic,"Disconnected, will sent",qos=1,retain=True)
        client.connect(broker, port)
        client.loop_start()
        while not self.is_connected: pass
        client.subscribe(self.message_topic,1)
        #client.message_callback_add(f"Devices/commands/{self.UID}", self.command_callback)
        client.subscribe(self.command_topic,1)
        return client
    
    def command_callback(self,client, userdata, message):
        print(
            f"Command {message.payload}, {message.topic=},{message.qos=},{message.retain=} ")
    def message_callback(self,client, userdata, message):
            print("message received ", str(message.payload))
            print("message topic=", message.topic)
            print("message qos=", message.qos)
            print("message retain flag=", message.retain)
    def publish(self, topic_root, data,qos=0,retain=False):
        # time.sleep(self.sleep_time)
        # total_count += 1
        topic="".join([topic_root,"/",self.UID]).replace("//","/")
        try:
            self.client.lastmsg = self.client.publish(topic, data,qos=qos,retain=retain)
        except:
            print("Unhandled exception in mqtt publish")

    def disconnect(self):
        self.publish("Pulse/leafs/","Disconnected,cleanly disconnected")
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
    mac_address="123"
    miami = MQTT(get_secrets("Azure"),mac_address)
    # azure.sleep_time=1
    # node=pulse()
    # node.update()
    while not miami.is_connected:#wait until connect to publish
        pass
    miami.publish("Pulse/leafs","Connected",qos=1,retain=True)
    while 1:
        message = input("Type a message, or type \"EXIT\"")
        if (message == "EXIT"):
            break
        else:
            miami.publish("test/", message)
    miami.disconnect()
