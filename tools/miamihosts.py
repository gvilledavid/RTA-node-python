#!/bin/python3

import os, sys, time, subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from tools.MQTT import get_mac


def convert_function():
    lookup = [
        ["ceNodeDev000", "E4:5F:01:A6:E5:BA", "E4:5F:01:A6:E5:BC", "10.130.56.201"],
        ["ceNodeDev001", "DC:A6:32:70:42:EE", "DC:A6:32:70:42:EF", "10.130.56.202"],
        ["ceNodeDev002", "DC:A6:32:E9:3A:AB", "DC:A6:32:E9:3A:AC", "10.130.56.203"],
        ["ceNodeDev003", "E4:5F:01:A6:E5:EC", "E4:5F:01:A6:E5:ED", "10.130.56.204"],
        ["ceNodeDev004", "E4:5F:01:A6:E5:FB", "E4:5F:01:A6:E5:FC", "10.130.56.205"],
        ["ceNodeDev005", "E4:5F:01:A6:E5:E6", "E4:5F:01:A6:E5:E7", "10.130.56.206"],
        ["ceNodeDev006", "E4:5F:01:DB:9F:3B", "E4:5F:01:DB:9F:3D", "10.130.56.207"],
        ["ceNodeDev007", "E4:5F:01:A6:E4:BE", "E4:5F:01:A6:E4:C1", "10.130.56.208"],
        ["ceNodeDev008", "E4:5F:01:DB:E5:4F", "E4:5F:01:DB:E5:50", "10.130.56.209"],
        ["ceNodeDev009", "E4:5F:01:DB:CE:4C", "E4:5F:01:DB:CE:4D", "10.130.56.210"],
        ["ceNodeDev010", "E4:5F:01:DB:E1:E6", "E4:5F:01:DB:E1:EA", "10.130.56.211"],
        ["ceNodeDev011", "E4:5F:01:DB:9E:8C", "E4:5F:01:DB:9E:8D", "10.130.56.212"],
        ["ceNodeDev012", "E4:5F:01:DB:E6:94", "E4:5F:01:DB:E6:95", "10.130.56.213"],
        ["ceNodeDev013", "E4:5F:01:DB:E6:BE", "E4:5F:01:DB:E6:BF", "10.130.56.214"],
        ["ceNodeDev014", "E4:5F:01:DB:D8:4E", "E4:5F:01:DB:D8:4F", "10.130.56.215"],
        ["ceNodeDev015", "E4:5F:01:DB:E6:82", "E4:5F:01:DB:E6:84", "10.130.56.216"],
        ["ceNodeDev022", "E4:5F:01:24:FA:33", "e4:5f:01:24:fa:35", "10.130.56.217"],
        ["ceNodeDev023", "E4:5F:01:56:AB:EB", "e4:5f:01:56:AB:ed", "10.130.56.218"],
        ["ceNodeDev024", "E4:5F:01:24:F9:8A", "e4:5f:01:24:f9:8b", "10.130.56.219"],
        ["ceNodeDev025", "E4:5F:01:25:13:6D", "e4:5f:01:25:13:6e", "10.130.56.220"],
        ["ceNodeDev026", "E4:5F:01:24:75:36", "e4:5f:01:24:75:37", "10.130.56.221"],
        ["ceNodeDev027", "E4:5F:01:0E:9C:22", "e4:5f:01:0e:9c:23", "10.130.56.222"],
        ["ceNodeDev028", "E4:5F:01:47:F7:37", "e4:5f:01:47:f7:38", "10.130.56.223"],
        ["ceNodeDev029", "E4:5F:01:24:DF:E0", "e4:5f:01:24:df:e1", "10.130.56.224"],
        ["ceNodeDev030", "E4:5F:01:24:54:CC", "e4:5f:01:24:54:cd", "10.130.56.225"],
        ["ceNodeDev031", "E4:5F:01:24:E0:01", "e4:5f:01:24:e0:02", "10.130.56.226"],
    ]
    dict = {}
    for device in lookup:
        dict[device[1].replace(":", "").lower()] = device[0]
        dict[device[2].replace(":", "").lower()] = device[0]
    print(dict)


def get_Miami_Hostname(host):
    # accept either eth0 or wlan 0 and lookup the hostname we should use in Miami

    dict = {
        "e45f01a6e5ba": "ceNodeDev000",
        "e45f01a6e5bc": "ceNodeDev000",
        "dca6327042ee": "ceNodeDev001",
        "dca6327042ef": "ceNodeDev001",
        "dca632e93aab": "ceNodeDev002",
        "dca632e93aac": "ceNodeDev002",
        "e45f01a6e5ec": "ceNodeDev003",
        "e45f01a6e5ed": "ceNodeDev003",
        "e45f01a6e5fb": "ceNodeDev004",
        "e45f01a6e5fc": "ceNodeDev004",
        "e45f01a6e5e6": "ceNodeDev005",
        "e45f01a6e5e7": "ceNodeDev005",
        "e45f01db9f3b": "ceNodeDev006",
        "e45f01db9f3d": "ceNodeDev006",
        "e45f01a6e4be": "ceNodeDev007",
        "e45f01a6e4c1": "ceNodeDev007",
        "e45f01dbe54f": "ceNodeDev008",
        "e45f01dbe550": "ceNodeDev008",
        "e45f01dbce4c": "ceNodeDev009",
        "e45f01dbce4d": "ceNodeDev009",
        "e45f01dbe1e6": "ceNodeDev010",
        "e45f01dbe1ea": "ceNodeDev010",
        "e45f01db9e8c": "ceNodeDev011",
        "e45f01db9e8d": "ceNodeDev011",
        "e45f01dbe694": "ceNodeDev012",
        "e45f01dbe695": "ceNodeDev012",
        "e45f01dbe6be": "ceNodeDev013",
        "e45f01dbe6bf": "ceNodeDev013",
        "e45f01dbd84e": "ceNodeDev014",
        "e45f01dbd84f": "ceNodeDev014",
        "e45f01dbe682": "ceNodeDev015",
        "e45f01dbe684": "ceNodeDev015",
        "e45f0124fa33": "ceNodeDev022",
        "e45f0124fa35": "ceNodeDev022",
        "e45f0156abeb": "ceNodeDev023",
        "e45f0156abed": "ceNodeDev023",
        "e45f0124f98a": "ceNodeDev024",
        "e45f0124f98b": "ceNodeDev024",
        "e45f0125136d": "ceNodeDev025",
        "e45f0125136e": "ceNodeDev025",
        "e45f01247536": "ceNodeDev026",
        "e45f01247537": "ceNodeDev026",
        "e45f010e9c22": "ceNodeDev027",
        "e45f010e9c23": "ceNodeDev027",
        "e45f0147f737": "ceNodeDev028",
        "e45f0147f738": "ceNodeDev028",
        "e45f0124dfe0": "ceNodeDev029",
        "e45f0124dfe1": "ceNodeDev029",
        "e45f012454cc": "ceNodeDev030",
        "e45f012454cd": "ceNodeDev030",
        "e45f0124e001": "ceNodeDev031",
        "e45f0124e002": "ceNodeDev031",
    }
    return dict.get(host.replace(":", "").lower(), None)


if __name__ == "__main__":
    TIMEOUTMAX = 9
    timeout = 0
    time.sleep(30)  # wait for the commands driver to start
    hostname = get_Miami_Hostname(get_mac("eth0"))
    while (
        hostname
        != str(subprocess.check_output("hostname", shell=True).strip(b"\n"))[2:-1]
    ):
        time.sleep(10)
        with open("/dev/piCOMM/hostname", "w") as f:
            f.write(hostname)
        timeout += 1
        if timeout > TIMEOUTMAX:
            break
