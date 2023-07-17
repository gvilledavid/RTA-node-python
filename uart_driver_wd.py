import sys
import os
import time
import subprocess
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, PatternMatchingEventHandler

import RPi.GPIO as GPIO

LOGFILE = "wd/wdlog.txt"  # /home/ceadmin/RTA/logs/wdlog.txt
STATUSDIR = "wd/"  # /dev/piUART/

# UART02   tx rx cts rts
# UART03                 tx rx cts rts
# UART04                               tx rx cts rts
# UART05                                             tx rx
# UART00                                                   tx rx cts rts
uart_list=[0 ,1, 2,  3,  4, 5, 6,  7,  8, 9, 10, 11, 12,13,14,15,16, 17 ] #BCM
EN=20 #low to enable chips
force_on=18 #low to enable autopower down
force_off=19 #high to enable drivers
invalid=[24,25,26,27] #goes high when valid rs232 signals detected by reciever

def init_gpios():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup( [ EN, force_on, force_off ],GPIO.OUT)
    GPIO.output(EN, GPIO.LOW)
    GPIO.output(force_on, GPIO.HIGH)#high will disable auto powerdown
    GPIO.output(force_off,GPIO.HIGH)
    GPIO.setup(invalid,GPIO.IN)
    with open(os.path.join(STATUSDIR,"force_on") )as f:
        f.write('1')
    with open(os.path.join(STATUSDIR,"force_off") )as f:
        f.write('1')
    with open(os.path.join(STATUSDIR,"enable") )as f:
        f.write('0')
    
        
    setup interupts
    [GPIO.input(x) for x in invalid]
    write to status/ttyAMA
def check_root():
    return True
    # if os.geteuid() != 0:
    #    return False
    # return True


def get_interfaces(logger):
    interfaces = []
    try:
        for x in str(
            subprocess.check_output("sudo dmesg |grep -e ttyAMA[1-4]", shell=True)
        )[2:-3].split("\\n"):
            index = x.find("tty")
            tty = x[index : index + 8].strip(" ")
            interfaces.append(tty)
    except:
        logger.critical("No interfaces found!")
        interfaces = ["ttyAMA1", "ttyAMA2", "ttyAMA3", "ttyAMA4"]
    return interfaces


def make_filestructure(logger):
    if os.path.isdir(STATUSDIR):
        os.chmod(STATUSDIR, 0o664)
    else:
        os.mkdir(STATUSDIR, mode=0o666)

    status_path = os.path.join(STATUSDIR, "status/")
    if os.path.isdir(status_path):
        os.chmod(status_path, 0o664)
    else:
        os.mkdir(os.path.join(STATUSDIR, "status/"), mode=0o664)
    with open(os.path.join(STATUSDIR, "enable"), "w") as f:
        f.write("0")
    with open(os.path.join(STATUSDIR, "force_on"), "w") as f:
        f.write("0")
    with open(os.path.join(STATUSDIR, "force_off"), "w") as f:
        f.write("0")
    for interface in get_interfaces(logger):
        if interface:
            with open(os.path.join(STATUSDIR, "status/", interface), "w") as f:
                f.write("0")
    arr = []
    lls(STATUSDIR, arr)
    print(arr)
    logger.info(f"Created driver structure:")
    for f in arr:
        logger.info(f)


def lls(path, arr=[]):
    path = os.path.normpath(path)
    if os.path.isfile(path):
        arr.append(path)
    elif os.path.isdir(path):
        arr.append(path)
        for f in os.listdir(path):
            lls(os.path.join(path, f), arr)
    return arr


def shutdown(logger, observer):
    # cleanup gpios
    observer.stop()
    observer.join
    logger.info("shutting down")
    logger.shutdown()


def start_watchdog(logger):
    class Handler(PatternMatchingEventHandler):
        def __init__(self):
            PatternMatchingEventHandler.__init__(
                self,
                patterns=["*/force_on", "*/force_off", "*/enable"],
                ignore_directories=True,
            )
            self.last_vals = [0, 0, 0]  # on,off,en

        def on_modified(self, event):
            logger.info(f"event on {event.src_path}")
            if os.path.samefile(event.src_path, os.path.join(STATUSDIR, "force_on")):
                index = 0
                pin=force_on
            elif os.path.samefile(event.src_path, os.path.join(STATUSDIR, "force_off")):
                index = 1
                pin=force_off
            elif os.path.samefile(event.src_path, os.path.join(STATUSDIR, "enable")):
                index = 2
                pin=EN
            else:
                index = -1
                pin=None
            if index >= 0:
                logger.info(f"Previously: {self.last_vals[index]}")
                with open(event.src_path, "r") as f:
                    val = f.readline()
                    logger.info(f"written val:{val}")
                    if val[0] == ("0" if self.last_vals[index] else "1"):
                        self.last_vals[index] = 0 if self.last_vals[index] else 1
                        level=GPIO.HIGH if val[0]=='1' else GPIO.LOW
                        GPIO.output(pin, level)
                        logger.info(f"GPIO {pin} written {level}")
                        # rpi.gpio(force_on,GPIO.LOW if self.last_vals[index] else gpio.high)
                    elif val[0] == ("1" if self.last_vals[index] else "0"):
                        pass
                    else:
                        with open(event.src_path, "w") as f:
                            f.write(str(self.last_vals[index]))

                    logger.info(f"new val:{self.last_vals[index]}")

    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, path=STATUSDIR, recursive=False)
    observer.start()
    return


def main():
    # first verify log directory and start logger
    log_dir, _ = os.path.split(LOGFILE)
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir, mode=0o666)
    logging.basicConfig(
        filename=LOGFILE,
        filemode="a",
        level=logging.DEBUG,
        format="%(asctime)s, %(msecs)d %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.info("Started process.")
    if check_root():
        logging.info("User is root")
    else:
        logging.critical("User is not root, terminating...")
        return
    make_filestructure(logging)
    init_gpios()
    observer = start_watchdog(logging)
    try:
        while True:
            time.sleep(5)
    except:
        shutdown(logging, observer)


if __name__ == "__main__":
    main()
