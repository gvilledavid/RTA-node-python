#!/bin/bash
#add ceadmin to groups:
#ceadmin adm dialout cdrom sudo dip video plugdev input lxd lpadmin sambashare spi i2c gpio spiuser 
devices=("ttyAMA0" "ttyAMA1" "ttyAMA2" "ttyAMA3" "ttyAMA4" "ttyUSB0")
mkdir -p /dev/piUART/status
for i in ${!devices[@]}; do
	sudo chmod +666 "/dev/${devices[$i]}"
	stty sane  38400 cs8 -parenb -ixon -crtscts -echo -F "/dev/${devices[$i]}"
	echo "0" |sudo tee "/dev/piUART/status/${devices[$i]}"
	echo "/dev/${devices[$i]}"
done

sudo adduser ceadmin dialout


groups=("adm" "dialout" "cdrom" "sudo" "dip" "video" "plugdev" "input" "lxd" "lpadmin" "sambashare" "spi" "i2c" "gpio" "spiuser")
for i in ${!groups[@]}; do
	sudo adduser ceadmin "${groups[$i]}"
	echo "adding group ${groups[$i]}"
done



#to call a program in the backgroup and store pid:
# nohup ./test.sh & echo $! >pid.txt
#later:
# kill -9 $(cat pid.txt)ls
