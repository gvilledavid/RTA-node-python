#!/bin/bash

while true
do
topic=$(ip link show eth0|grep -o -E "(.{2}:){5}.{2}\s")
eth="$(ip address show eth0 |grep -o -E 'inet .*/')"
#eth= $(ip address show eth0  | grep -o -E 'inet ((25[0-5]|2[0-4][0-9]|[1]?[1-9][0-9]?).){3}(25[0-5]|2[0-4][0-9]|[1]?[1-9]?[0-9])')
wlan=$(ip address show wlan0 | grep -o -E 'inet ((25[0-5]|2[0-4][0-9]|[1]?[1-9][0-9]?).){3}(25[0-5]|2[0-4][0-9]|[1]?[1-9]?[0-9])')
host=$(hostname)
eth="${eth////}"
eth="${eth/inet /}"
wlan="${wlan/inet /}"
echo "topic is $topic"
message="{\"hostname\":\"$host\",\"wlan\":\"$wlan\",\"eth\":\"$eth\"}"
echo "message is $message"

mosquitto_pub -h atbwkuozvbuys-ats.iot.us-east-1.amazonaws.com -t "test/node/$topic" -m "$message" -p 8883 --cafile /usr/local/share/.secrets/AWS/AmazonRootCA1.pem --cert /usr/local/share/.secrets/AWS/547e42f7d374d8391941bf31376d7671659d40a23e941a3b6ced9ba17e6fbad7-certificate.pem.crt --key /usr/local/share/.secrets/AWS/547e42f7d374d8391941bf31376d7671659d40a23e941a3b6ced9ba17e6fbad7-private.pem.key --insecure -d


sleep 60
done