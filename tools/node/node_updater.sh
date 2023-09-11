#!/bin/bash
cd /usr/src/RTA/
rm -rf RTA-node-python
git clone --branch test "$(cat /usr/local/share/.secrets/git.store)"/Convergent-Engineering/RTA-node-python.git
mv -f /usr/src/RTA/tools/node/* /usr/src/RTA/node/.