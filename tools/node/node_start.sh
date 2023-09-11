#!/bin/bash
sleep 3
cd /usr/src/RTA/RTA-node-python/node_manager/
nohup python3 NodeManager.py >/dev/null 2>&1 &
echo $!>/usr/src/RTA/node/node_pid.file