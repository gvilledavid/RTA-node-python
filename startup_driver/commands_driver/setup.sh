#!/bin/bash

cd /usr/src/RTA/commands_driver/
sudo apt install python3-pip -y
sudo pip3 install RPI.GPIO
sudo pip3 install watchdog
nohup sudo python3 commands_driver_wd.py >/dev/null 2>&1 &
echo $! >pid.file
