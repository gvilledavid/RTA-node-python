import random
import time
import ssl
import json
import traceback
import os, sys
import re
import queue
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from tools.RotatingLogger import RotatingLogger


class get_secrets:
    # store secrets in secrets_folder="/usr/local/share/.secrets/"
    #   broker/
    #       address.txt =address:port\nuser\npassword
    #       cert.pem
    #       private.pem
    #       CA.pem
    def __init__(self, broker, logger=None):
        if not logger:
            self.logger = RotatingLogger("get_secrets.log")
        else:
            self.logger = logger
        root_dir = os.path.abspath("/usr/local/share/.secrets/")
        self.broker = broker
        self.logger.info(f"Running get_secrets using {root_dir}")
        try:
            with open(os.path.join(root_dir, broker, "address.txt"), "r") as f:
                self.address, port = f.readline().replace("\n", "").split(":")
                self.port = int(port)
                if not self.port:
                    self.port = 1883  # default mqtt port
                if not self.address:
                    self.logger.critical("Address not specified in address.txt")
                    raise Exception("Address not specified in address.txt")
                self.username = f.readline().replace(
                    "\n", ""
                )  # returns empty line if nothing there
                self.password = f.readline().replace("\n", "")
        except:
            self.logger.critical(
                f"address.txt for {self.broker} does not exist or is not formatted correctly."
            )
        self.cert_file = os.path.join(root_dir, broker, "cert.pem")
        self.key_file = os.path.join(root_dir, broker, "private.pem")
        self.CA_file = os.path.join(root_dir, broker, "CA.pem")
        self.using_CA = os.path.isfile(self.CA_file)
        print(self.cert_file, self.key_file)
        self.cert = self.parse_pem(self.cert_file)
        self.key = self.parse_pem(self.key_file)
        if self.using_CA:
            self.CA = self.parse_pem(self.CA_file)

    def parse_pem(self, file):
        if not os.path.isfile(file):
            raise Exception(f"{file} does not exist")
        try:
            with open(file, "r") as f:
                x = f.read()
                x = re.sub("^[-]{5}.*[-]*$", "", x, flags=re.MULTILINE).replace(
                    "\n", ""
                )
            return x
        except:
            print(f"Could not open and parse{file}")
            return ""
