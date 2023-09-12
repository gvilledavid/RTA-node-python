#!/bin/bash
sleep 10
cd /usr/src/RTA/node
nohup ./pulse.sh >/dev/null 2>&1 &
echo $!>pid.file