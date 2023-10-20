#!/bin/bash
#copy RTA_installer folder using scp or something
#run this file to install on a new image of ubuntu 22.04.3LTS from the rpi imager

#todo: script that generates and zips RTA_installer folder from a working device

BASE_RTA_INSTALLER_DIR=$(dirname "$0")
#initial update
sudo apt update
sudo apt upgrade -y 


#login stuff
sudo apt install openssh-server -y
mkdir -p /home/ubuntu/.ssh/
cp $BASE_RTA_INSTALLER_DIR/home/ubuntu/.ssh/* /home/ubuntu/.ssh/.
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
sudo cp $BASE_RTA_INSTALLER_DIR/etc/ssh/sshd_config /etc/ssh/sshd_config
sudo cp $BASE_RTA_INSTALLER_DIR/etc/ssh/sshd_config.d/* /etc/ssh/sshd_config.d/.
sudo systemctl reload ssh


#install requirements
sudo apt install mosquitto-clients -y
sudo apt install python3 -y
sudo apt-get install python3-pip -y
sudo -H -u ubuntu pip install -r $BASE_RTA_INSTALLER_DIR/requirements.txt
sudo pip install -r $BASE_RTA_INSTALLER_DIR/root_requirements.txt


#update wifi netplan:
sudo cp $BASE_RTA_INSTALLER_DIR/etc/netplan/netplan.yaml /etc/netplan/netplan.yaml 
sudo netplan apply /etc/netplan/netplan.yaml 


#install overlays:
#todo: check ubuntu version and load specific things here
sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.bak
sudo cp /boot/firmware/config.txt  /boot/firmware/config.txt.bak
sudo cp /boot/firmware/syscfg.txt  /boot/firmware/syscfg.txt.bak
sudo cp /boot/firmware/usercfg.txt /boot/firmware/usercfg.txt.bak
sudo cp $BASE_RTA_INSTALLER_DIR/boot/firmware/cmdline.txt /boot/firmware/cmdline.txt
sudo cp $BASE_RTA_INSTALLER_DIR/boot/firmware/config.txt  /boot/firmware/config.txt
sudo cp $BASE_RTA_INSTALLER_DIR/boot/firmware/syscfg.txt  /boot/firmware/syscfg.txt
sudo cp $BASE_RTA_INSTALLER_DIR/boot/firmware/usercfg.txt /boot/firmware/usercfg.txt
stty sane  115200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA0
stty sane  115200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA1
stty sane  115200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA2
stty sane  115200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA3
stty sane  115200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA4


#install certificates:
sudo mkdir -p /usr/local/share/.secrets/
sudo chmod --recursive +777  /usr/local/share/.secrets
cp -r $BASE_RTA_INSTALLER_DIR/usr/local/share/.secrets /usr/local/share/.


#install NodeManager
sudo mkdir -p /usr/src/RTA/
sudo chown -R ubuntu:ubuntu /usr/src/RTA/
cd /usr/src/RTA/
git clone --branch test "$(cat /usr/local/share/.secrets/git.store)"/Convergent-Engineering/RTA-node-python.git
sudo chmod +x /usr/src/RTA/RTA-node-python/tools/node/node_updater.sh
sudo /usr/src/RTA/RTA-node-python/tools/node/node_updater.sh
