#!/bin/bash
echo "Killing old process..."
kill $(cat /usr/src/RTA/node/node_pid.file)
sleep 3
echo "Deleting old files."
cd /usr/src/RTA/
rm -rf RTA-node-python
echo "Cloning new repo."
git clone --branch test "$(cat /usr/local/share/.secrets/git.store)"/Convergent-Engineering/RTA-node-python.git
echo "Moving /usr/src/RTA/node scripts"
mv -f /usr/src/RTA/RTA-node-python/tools/node/* /usr/src/RTA/node/.
chmod +777 /usr/src/RTA/node/node_updater.sh
chmod +777 /usr/src/RTA/node/start.sh
chmod +777 /usr/src/RTA/node/pulse.sh
chmod +777 /usr/src/RTA/node/node_start.sh
chmod +777 /usr/src/RTA/node/gpiostat.sh
echo "Starting NodeManager..."
/bin/bash /usr/src/RTA/node/node_start.sh
echo "Done"
echo "PID of NodeManager: $(cat node_pid.file)"