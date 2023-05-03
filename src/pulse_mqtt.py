
import random
import time
import paho.mqtt.client as mqtt
import ssl
import json
import traceback
from pulse.pulse import pulse
import os
import re

class MQTT:
    def __init__(self, secrets):
        self.last_packet = {"last_time": time.time()}
        self.secrets=secrets
        self.client = self.connect_mqtt(secrets.address, secrets.port, secrets.cert_file, secrets.key_file)
        self.client.loop_start()
        self.sleep_time=5
    #todo: on_disconnect function
    #todo: subscribe to commands
    def connect_mqtt(self, broker, port, cert_file, key_file):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"Connected to MQTT Broker {self.secrets.broker}!")
            else:
                print("Failed to connect, return code %d\n", rc)

        client = mqtt.Client()
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=None)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file, password=None)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        client.tls_set_context(context)

        client.on_connect = on_connect
        client.connect(broker, port)
        return client
    
    def publish(self, topic,data):
        #time.sleep(self.sleep_time) 
        #total_count += 1
        try:
            msg, result = self.client.publish(topic,data)
        except:
            print("Unhandled exception in mqtt publish")

class get_secrets():
    #store secrets in secrets_folder="/usr/local/share/.secrets/"
    #   broker/
    #       address.txt =address:port
    #       cert.pem
    #       private.pem
    #       CA.pem
    def __init__(self,broker):
        root_dir="/usr/local/share/.secrets/"
        self.broker=broker
        try:
            with open(os.path.join(root_dir,broker,"address.txt"),'r') as f:
                self.address,port=f.readline().replace("\n","").split(":")
                self.port=int(port)
        except:
            print(f"address.txt for {broker} does not exist or is not formatted correctly.")
        self.cert_file=os.path.join(root_dir,broker,"cert.pem")
        self.key_file=os.path.join(root_dir,broker,"private.pem")
        self.cert=self.parse_pem(self.cert_file)
        self.key=self.parse_pem(self.key_file)
    def parse_pem(self,file):
        try:
            with open(file,'r') as f :
                x= f.read()
                x= re.sub("^[-]{5}.*[-]*$","",x,flags=re.MULTILINE).replace("\n","")
            return x
        except:
            print(f"Could not open and parse{file}")
            return ""


if __name__ == '__main__':
    azure = MQTT(get_secrets("Azure"))
    aws = MQTT(get_secrets("AWS"))
    #miami=MQTT(get_secrets("cebabletier"))
    azure.sleep_time=1
    node=pulse()
    node.update()
    count=0
    while 1:
        time.sleep(.5)
        node.update()
        azure.publish(node.legacy_topic,node.legacy_pulse)
        if (count>10):
            count=0
            aws.publish(node.pulse_topic,node.pulse)
            azure.publish(node.pulse_topic,node.pulse)
        elif(not count%2):
            aws.publish(node.pulse_topic,node.brief)
            azure.publish(node.pulse_topic,node.brief)
        count+=1