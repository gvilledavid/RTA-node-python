#!/bin/bash

cd /usr/src/RTA/uart_driver/
sudo apt install python3-pip -y
sudo pip3 install RPI.GPIO
sudo pip3 install watchdog
nohup sudo python3 uart_driver_wd.py >/dev/null 2>&1 &
echo $! >pid.file
