#!/bin/bash
devices=("ttyAMA0" "ttyAMA1" "ttyAMA2" "ttyAMA3" "ttyAMA4" "ttyUSB0")
mkdir -p /dev/piUART/status
for i in ${!devices[@]}; do
	sudo chmod +666 "/dev/${devices[$i]}"
	stty sane  38400 cs8 -parenb -ixon -crtscts -echo -F "/dev/${devices[$i]}"
	echo "0" |sudo tee "/dev/piUART/status/${devices[$i]}"
	echo "/dev/${devices[$i]}"
done