e4:5f:01:db:e6:94 = {"hostname":"ceNodeDev012","wlan":"","eth":"10.66.103.230"}
e4:5f:01:db:e6:be = {"hostname":"ceNodeDev013","wlan":"","eth":"10.66.103.148"}
e4:5f:01:0e:9c:22 = {"hostname":"ceNodeDev027","wlan":"","eth":"10.66.103.246"}
e4:5f:01:a6:e5:ec = {"hostname":"ceNodeDev003","wlan":"","eth":"10.66.103.216"}
e4:5f:01:24:df:e0 = {"hostname":"ceNodeDev029","wlan":"","eth":"10.66.103.120"}
e4:5f:01:24:75:36 = {"hostname":"ceNodeDev026","wlan":"","eth":"10.66.103.232"}
e4:5f:01:24:f9:8a = {"hostname":"ceNodeDev024","wlan":"","eth":"10.66.103.245"}
e4:5f:01:24:54:cc = {"hostname":"ceNodeDev030","wlan":"","eth":"10.66.103.167"}
e4:5f:01:47:f7:37 = {"hostname":"ceNodeDev028","wlan":"","eth":"10.66.103.180"}
e4:5f:01:25:13:6d = {"hostname":"ceNodeDev025","wlan":"","eth":"10.66.103.203"}
e4:5f:01:24:e0:01 = {"hostname":"ceNodeDev031","wlan":"","eth":"10.66.103.198"}
e4:5f:01:db:ce:4c = {"hostname":"ceNodeDev009","wlan":"10.1.1.169","eth":""}

run this:
CREDENTIALS="https://user:key@github.com"
sudo killall python3
sudo rm -rf /usr/src/RTA/RTA-node-python
cd /usr/src/RTA/
echo  -n $CREDENTIALS>/usr/local/share/.secrets/git.store
git clone --branch test "$(cat /usr/local/share/.secrets/git.store)"/Convergent-Engineering/RTA-node-python.git
sudo chmod +x /usr/src/RTA/RTA-node-python/tools/node/node_updater.sh
sudo /usr/src/RTA/RTA-node-python/tools/node/node_updater.sh
ip link


