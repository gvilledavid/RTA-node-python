#!/bin/bash
sudo apt update -y
export DEBIAN_FRONTEND=noninteractive
sudo -E apt-get -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef" dist-upgrade -q -y --allow-downgrades --allow-remove-essential --allow-change-held-packages
sudo apt-get autoremove
sudo apt-get autoclean
if [ -f /var/run/reboot-required ]; then
  #kill node manager
  echo "Killing old process..."
  kill -TERM $(cat /usr/src/RTA/node/node_pid.file)
  sleep 3
  sudo shutdown -r 0
fi