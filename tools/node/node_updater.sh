#!/bin/bash
if whoami |grep root
then
    echo "Elevated permissions"
else
    echo "Run as root, exiting"
    exit
fi
echo "Killing old process..."
kill -TERM $(cat /usr/src/RTA/commands_driver/pid.file)
echo "commands driver down"
kill -TERM $(cat /usr/src/RTA/node/node_pid.file)
echo "Node down"
kill -TERM $(cat /usr/src/RTA/uart_driver/pid.file)
echo "uart manager down"

sleep 3
echo "Deleting old files."
cd /usr/src/RTA/
rm -rf RTA-node-python
rm -rf uart_driver
rm -rf commands_driver

echo "Cloning new repo."
if [ $# -eq 0 ]
then
        BRANCH="test"
else
        BRANCH=$1
fi
echo "Using github branch $BRANCH"

git clone --branch $BRANCH "$(cat /usr/local/share/.secrets/git.store)"/Convergent-Engineering/RTA-node-python.git
echo "Moving /usr/src/RTA/node scripts"
mkdir -p /usr/src/RTA/node/
mv -f /usr/src/RTA/RTA-node-python/tools/node/* /usr/src/RTA/node/.
chmod +777 /usr/src/RTA/node/*.sh

echo "Moving startup drivers"
#mkdir -p /usr/src/RTA/uart_driver
#mkdir -p /usr/src/RTA/commands_driver
cp -r /usr/src/RTA/RTA-node-python/startup_driver/commands_driver  /usr/src/RTA/commands_driver
cp -r /usr/src/RTA/RTA-node-python/startup_driver/uart_driver  /usr/src/RTA/uart_driver
#restart the startup drivers as root
chmod +777 /usr/src/RTA//uart_driver/setup.sh
chmod +777 /usr/src/RTA/commands_driver/setup.sh
echo "Starting startup_drivers"
sudo /usr/src/RTA/commands_driver/setup.sh
sudo /usr/src/RTA/uart_driver/setup.sh

echo "Changing ownership of directories"
chown -R ubuntu:ubuntu /usr/src/RTA
chown ubuntu:ubuntu /usr/src/RTA/*

#restart heartbeat backup
kill -9 $(cat /usr/src/RTA/node/pid.file)
sudo -H -u ubuntu bash -c /usr/src/RTA/node/start.sh

#install requirements using python requirements.txt that we should include somewhere in the repo
# for now:
sudo -H -u ubuntu pip install numpy
sudo -H -u ubuntu pip install debugpy
sudo -H -u ubuntu pip install paho_mqtt

sleep 10
echo "Starting NodeManager..."
#/bin/bash /usr/src/RTA/node/node_start.sh
sleep 3
cd /usr/src/RTA/RTA-node-python/node_manager/
sudo -H -u ubuntu bash -c /usr/src/RTA/node/node_start.sh

#verify crontab
cd /usr/src/RTA/node/
sudo crontab -u root  -l > root_crontab.txt
sudo crontab -u ubuntu  -l > ubuntu_crontab.txt

if grep "/usr/src/RTA/uart_driver/setup.sh" root_crontab.txt
then
    echo "uart_driver exists in root crontab"
else
    echo "adding uart_driver to root crontab"
    echo "@reboot /usr/src/RTA/uart_driver/setup.sh">>root_crontab.txt
fi
if grep "/usr/src/RTA/commands_driver/setup.sh" root_crontab.txt
then
    echo "commands_driver exists in root crontab"
else
    echo "adding commands_driver to root crontab"
    echo "@reboot /usr/src/RTA/commands_driver/setup.sh">>root_crontab.txt
fi
#unnatended updates should also be in root crontab I guess
if grep "/usr/src/RTA/RTA-node-python/tools/miamihosts.py" ubuntu_crontab.txt
then
    echo "miamihosts.py exists in ubuntu crontab"
else
    echo "adding miamihosts.py to ubuntu crontab"
    echo "@reboot /usr/src/RTA/RTA-node-python/tools/miamihosts.py">>ubuntu_crontab.txt
fi
if grep "/usr/src/RTA/node/start.sh" ubuntu_crontab.txt
then
    echo "test pulse exists in ubuntu crontab"
else
    echo "adding test pulse to ubuntu crontab"
    echo "@reboot /usr/src/RTA/node/start.sh">>ubuntu_crontab.txt
fi
if grep "/usr/src/RTA/node/node_start.sh" ubuntu_crontab.txt
then
    echo "node manager exists in ubuntu crontab"
else
    echo "adding node manager to ubuntu crontab"
    echo "@reboot /usr/src/RTA/node/node_start.sh">>ubuntu_crontab.txt
fi
sudo crontab -u root  root_crontab.txt
#@reboot /usr/src/RTA/uart_driver/setup.sh
#@reboot /usr/src/RTA/commands_driver/setup.sh
sudo crontab -u ubuntu   ubuntu_crontab.txt
#@reboot /usr/src/RTA/RTA-node-python/tools/miamihosts.py
#@reboot /usr/src/RTA/node/start.sh
sudo rm root_crontab.txt
sudo rm ubuntu_crontab.txt
 
echo "Done"
echo "PID of NodeManager: $(cat /usr/src/RTA/node/node_pid.file)"
echo "PID of Uart Driver: $(cat /usr/src/RTA/uart_driver/pid.file)"
echo "PID of Commands Driver: $(cat /usr/src/RTA/commands_driver/pid.file)"

#update and restart, should be off by default and have an option in the future
sudo /usr/src/RTA/node/system_updater.sh