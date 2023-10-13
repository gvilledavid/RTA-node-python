#!/bin/bash
sleep 5
kill -9 $(cat pid.file)
echo "Starting arbitrary process...">>updater_example.txt
#for example:
#./node_manager