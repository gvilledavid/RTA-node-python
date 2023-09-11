#!/bin/bash
kill $(cat node_pid.file)
sleep 3
cd /usr/src/RTA/
rm -rf RTA-node-python
git clone --branch test "$(cat /usr/local/share/.secrets/git.store)"/Convergent-Engineering/RTA-node-python.git
mv -f /usr/src/RTA/RTA-node-python/tools/node/* /usr/src/RTA/node/.
chmod +777 /usr/src/RTA/node/node_updater.sh
chmod +777 /usr/src/RTA/node/start.sh
chmod +777 /usr/src/RTA/node/pulse.sh
chmod +777 /usr/src/RTA/node/node_start.sh
chmod +777 /usr/src/RTA/node/gpiostat.sh
./node/node_start.sh