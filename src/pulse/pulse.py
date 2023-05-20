#!/bin/python3

import os
import subprocess
import time
import json

class pulse:
    def __init__(self):
        self.UID=self.get_networking()[0]["mac"]
        self.rawpulse, self.legacy_topic, self.legacy_pulse = self.generate_node_pulse(1)
        self.brief = self.to_json(self.generate_brief_node_pulse(self.rawpulse))
        self.pulse=self.to_json(self.rawpulse)
        self.legacy_pulse=self.to_json(self.legacy_pulse)
        self.pulse_topic=f"Devices/pulse/{self.UID}"
    def update(self):
        starttime = time.time()
        self.pulse, self.legacy_topic, self.legacy_pulse = self.generate_node_pulse(1)
        self.brief = self.to_json(self.generate_brief_node_pulse(self.pulse))
        self.pulse=self.to_json(self.pulse)
        self.executiontime = (time.time() - starttime)
    def get_hostname(self):
        return str(subprocess.check_output("hostname", shell=True).strip(b'\n'))[2:-1]


    def set_hostname(self,name):
        ret = os.system(f'hostnamectl set-hostname {name}')
        return (1 if ret == 0 else 0)


    def get_hostname_verbose(self):
        dict = {"UID":self.UID}
        try:
            list = subprocess.check_output("hostnamectl").split(b'\n')
            for param in list if list[-1].find(b':') > 0 else list[:-1]:
                a, b = param.split(b':')
                dict[str(a)[2:-1].strip().replace(" ", "-")] = str(b)[2:-1].strip()
            Model = str(subprocess.check_output(
                "cat /proc/cpuinfo", shell=True))[2:-3]
            Model = Model[Model.find('Model'):]
            Model = Model[Model.find(":")+2:]
            dict["Model"] = Model
            dict["Ram"] = str(subprocess.check_output("free", shell=True))[
                2:-3].split('\\n')[1].split()[1]
            drive = str(subprocess.check_output("lsblk |grep mmc", shell=True))[
                2:-3].split('\\n')[0].split()
            dict["disk-size"] = drive[3]
            avail = 0
            for partition in str(subprocess.check_output(f"df |grep \"/dev/{drive[0]}\"", shell=True))[2:-3].split('\\n'):
                avail = avail+int(partition.split()[3])
            dict["disk-avail"] = avail

        except:
            print("call to hostnamectl failed")
        return dict


    def param_from_iface(self,iface_str, param):
        # will return "val" if f"{param} {val} " exists in iface_str
        # or will return "val" if iface_str ends in f"{param} {val}"
        # else returns ""
        #   only val of first param will be returned
        #   val should not have whitespaces in it and will end at, but not include, the first space after it
        #   last whitespace may be omitted if it is the end of iface_str
        # >>> param_from_iface(" 1 234 56 78","7")
        # ''
        # >>> param_from_iface(" 1 234 56 78","56")
        # '78'
        # >>> param_from_iface(" 1 234 1 56 78","234")
        # '1'
        index = iface_str.find(param+" ")
        if index == -1:
            return ""
        start_index = index+len(param)+1
        index = iface_str[start_index:].find(' ')
        if index != -1:
            return iface_str[start_index:start_index+index]
        else:
            return iface_str[start_index:]


    def get_networking(self):
        stdoutval = str(subprocess.check_output(
            "ip address show", shell=True))[2:-1]
        list = []
        link = 1
        while len(stdoutval) > 3:
            # start_index=0 if link==1 else start_index=2#ignore \\n on following lines
            end_index = stdoutval.find(f"\\n{link+1}")
            if end_index == -1:
                end_index = len(stdoutval)
            # print(end_index)
            this_link = stdoutval[:end_index]
            # print(f"link number: {link} is: \n{this_link}\n\n")
            list.append(this_link)
            stdoutval = stdoutval[end_index:].replace("\\n", "", 1)
            # print(f"remaining: {stdoutval}\n")
            link += 1
        # print(list)
        interfaces = []
        for link in list:
            iface = link[2:link[2:].find(":")+2].strip()
            mac = self.param_from_iface(link, 'link/ether')
            inet = self.param_from_iface(link, 'inet')
            inet6 = self.param_from_iface(link, 'inet6')
            if iface != "lo":
                interfaces.append({"name": iface, "mac": mac,
                                "ipv4": inet, "ipv6": inet6})
        return interfaces


    def get_hardware(self):
        # on vcgenmod errors, run: sudo usermod -aG video ceadmin
        try:
            # temperature:
            temperature = str(subprocess.check_output(
                "vcgencmd measure_temp", shell=True))
            temperature = temperature[temperature.find("=")+1:-3].replace('\'', '')
            # core voltage:
            voltage = str(subprocess.check_output(
                "vcgencmd measure_volts", shell=True))
            voltage = voltage[voltage.find("=")+1:-3]
        except:
            print("vcgenmod errors, run: sudo usermod -aG video <username>")
            return 0
        # throttling:
        # 111100000000000001010
        # ||||             ||||_ under-voltage
        # ||||             |||_ currently throttled
        # ||||             ||_ arm frequency capped
        # ||||             |_ soft temperature reached
        # ||||_ under-voltage has occurred since last reboot
        # |||_ throttling has occurred since last reboot
        # ||_ arm frequency capped has occurred since last reboot
        # |_ soft temperature reached since last reboot
        throttled_alerts = []
        throttling_status = {
            0: "currently-under-voltage",
            1: "currently-throttled",
            2: "currently-frequency-capped",
            3: "currently-soft-temp-reached",
            17: "previously-under-voltage",
            18: "previously-throttled",
            19: "previously-frequency-capped",
            20: "previously-soft-temp-reached"}
        try:
            throttled = str(subprocess.check_output(
                "vcgencmd get_throttled", shell=True))
        except:
            print("vcgenmod errors, run: sudo usermod -aG video <username>")
            return 0
        # throttled=throttled.replace("x0","x1e000f")#fake data
        throttled = throttled[throttled.find("=")+3:-3]
        if throttled == '0':
            throttled_alerts.append("no-alarms")
        else:
            # convert throttled to binary, check if any of the throttling_status bits are set, add those to the list
            binary = bin(int(throttled, 16))[2:].zfill(24)[::-1]
            # print(binary)
            for key in throttling_status:
                # print(key)
                if binary[int(key)] == '1':
                    throttled_alerts.append(throttling_status[key])
        # print(throttled_alerts)
        # uarts
        try:
            ttyAMA = subprocess.check_output("ls /dev/ |grep ttyAMA*", shell=True)
        except:
            ttyAMA = "b'\\n'"
        try:
            ttyUSB = subprocess.check_output("ls /dev/ |grep ttyUSB*", shell=True)
        except:
            ttyUSB = "b'\\n'"
        try:
            # uart.py will make and manage files in /dev/piUART/status
            ttyStatus = subprocess.check_output(
                "ls /dev/piUART/status", shell=True)
        except:
            ttyStatus = "b'\\n'"
        ttyAMA = str(ttyAMA)[2:-3].split("\\n")
        ttyUSB = str(ttyUSB)[2:-3].split("\\n")
        ttyStatus = str(ttyStatus)[2:-3].split("\\n")
        uarts = {}
        for uart in ttyAMA+ttyUSB:
            status = "?"
            if uart in ttyStatus:
                try:
                    status = int(str(subprocess.check_output(
                        f"cat /dev/piUART/status/{uart}", shell=True))[2:-3])
                except:
                    pass
            uarts[uart] = status
        # str temperature, str voltage, array throttled_alerts dict uarts
        return {"temp": temperature, "core-voltage": voltage, "throttled-status": throttled_alerts, "uarts": uarts}


    def get_battery(self):
        dict = {"status": "No battery",
                "Bat": 0,
                "battery-timeleft": 9999,
                "AC": "connected",
                "charge-voltage": 5,
                "battery-voltage": 0}
        return dict


    def get_time(self):
        timedatectl = str(subprocess.check_output(
            "timedatectl", shell=True))[2:-3].split("\\n")
        ret_dict = {}
        for line in timedatectl:
            if line.find(": ") < 0:
                break
            key, data = line.split(": ")
            if key == "Warning":
                break
            else:
                ret_dict[key.strip().replace(" ", "-")] = data.replace("\n","").strip()
        ret_dict["timestamp"] = str(int(time.time()*1000))
        return ret_dict


    def legacyPulse(self,mac, iface, ipv4, timestamp):
        mac = mac.lower().replace(":", "")
        topic = f"Device/Pulse/{mac}{mac}LeafPulse11/{mac}"
        message = "{\"l\":[{\"l\":[{\"l\":[{\"n\":\"MAC\",\"v\":\""+mac+"\"}],\"n\":\""+iface+"\",\"v\":\""+ipv4+"\"}],\"n\":\"if\",\"v\":null},{\"n\":\"ID\",\"v\":\"" + \
            mac+"\"},{\"n\":\"Pow\",\"v\":\"Charging\"},{\"n\":\"Bat\",\"v\":80},{\"n\":\"IID\",\"v\":\"1\"}],\"n\":\"Time\",\"v\":\""+timestamp+"\"}"
        return topic, message


    def dummy_connected_device(self,fake_data=0):
        if fake_data:
            return {"UID": "12:54:d3:3b:9e:8d:ttyAMA0", "DID": "35B1500404", "vent-type": "PB980",
                    "baud": 9600, "protocol": "840 DCI", "parent-node": "12:54:d3:3b:9e:8d", "device-status": "IDLE", "timestamp": str(int(time.time()*1000))}
        else:
            return {"UID": "", "DID": "", "vent-type": "",
                    "baud": "", "protocol": "", "parent-node": "", "device-status": "", "timestamp": str(int(time.time()*1000))}


    def connected_device(self,parent_node_mac, uart, did, vent_type, baud, protocol, status):
        return {"UID": f"{parent_node_mac}:{uart}", "DID": did, "vent-type": vent_type,
                "baud": baud, "protocol": protocol, "parent-node": parent_node_mac, "device-status": status,
                "timestamp": str(int(time.time()*1000))}


    def to_json(self,input_dict):
        # return json.dumps(dict,sort_keys=False)
        return str(input_dict).replace('\'', '"').replace("\n","")


    def generate_node_pulse(self,legacy=0):
        pulse = self.get_hostname_verbose()
        pulse["networking"] = self.get_networking()
        hw = self.get_hardware()
        pulse["temperature"] = hw["temp"]
        try:
            uptime = str(subprocess.check_output(
                "cat /proc/uptime", shell=True))[2:-3]
            pulse["uptime"] = uptime[:uptime.find(" ")]
        except:
            pass
        pulse["core-voltage"] = hw["core-voltage"]
        pulse["throttled-status"] = hw["throttled-status"]
        pulse["connected-leafs"] = hw["uarts"]
        pulse["battery"] = self.get_battery()
        dict_time = self.get_time()
        pulse["time"] = dict_time
        pulse["timestamp"] = dict_time.pop("timestamp")

        if legacy:
            for iface in pulse["networking"]:
                if iface["name"] == "wlan0":
                    wlan = iface
                elif iface["name"] == "eth0":
                    eth = iface
            try:
                mac = wlan["mac"]
                name = wlan["name"]
                ip = wlan["ipv4"]
            except:
                try:
                    mac = eth["mac"]
                    name = eth["name"]
                    ip = eth["ipv4"]
                except:
                    mac = " "
                    name = "wlan0"
                    ip = " "
            legacy_pulse_topic, legacy_pulse_message = self.legacyPulse(
                mac, name, ip, pulse["timestamp"])
            return pulse, legacy_pulse_topic, legacy_pulse_message
        return pulse
    def generate_brief_node_pulse(self,from_dict=0):
        if from_dict == 0:
            verbose_pulse = self.generate_node_pulse()
        else:
            verbose_pulse = from_dict
        brief_pulse = {"UID":self.UID}
        brief_pulse["Static-hostname"] = verbose_pulse["Static-hostname"]
        brief_pulse["networking"] = verbose_pulse["networking"]
        brief_pulse["connected-leafs"] = verbose_pulse["connected-leafs"]
        brief_pulse["battery"] = {"Bat": verbose_pulse["battery"]["Bat"]}
        brief_pulse["timestamp"] = verbose_pulse["timestamp"]
        return brief_pulse


if __name__ == "__main__":
    node=pulse()
    node.update()
    print(f"{node.pulse=}\n{node.pulse_topic=}\n{node.legacy_pulse=}\n{node.legacy_topic=}\n{node.brief=}\n{node.executiontime}")