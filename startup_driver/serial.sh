#!/bin/bash
stty sane  19200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA1
stty sane  19200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA2
stty sane  19200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA0
stty sane  115200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyAMA4
stty sane  115200 cs8 -parenb -ixon -crtscts -echo -F /dev/ttyUSB0
while true
do
    echo -n -e "AMA1 $(date)\n">/dev/ttyAMA1
    echo -n -e "AMA2 $(date)\n">/dev/ttyAMA2
    echo -n -e "AMA3 $(date)\n">/dev/ttyAMA3
    echo -n -e "AMA4 $(date)\n">/dev/ttyAMA4
    echo -n -e "USB0 $(date)\n">/dev/ttyUSB0
    sleep .1
done
