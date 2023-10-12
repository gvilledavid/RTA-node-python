import sys
import os
import time
import subprocess
import logging
from logging.handlers import RotatingFileHandler


class RotatingLogger:
    def __init__(
        self, logname, dir="/var/log/RTA/logs/", maxFileSize=65500, backupCount=5
    ):
        self.logfile = os.path.normpath(os.path.join(dir, logname))
        if not os.path.isdir(dir):
            # os.system(f"mkdir -p {dir}")  # os.mkdir(log_dir, mode=0o666)
            # os.system(f"sudo chmod -R +777 {log_dir}")
            os.makedirs(dir)
        self.UID = f"Rotating Logger {logname}:{str(int(time.time()))}"
        self.logger = logging.getLogger(self.UID)

        self.logger.setLevel(logging.NOTSET)
        self.handler = logging.handlers.RotatingFileHandler(
            self.logfile, "a", maxBytes=maxFileSize, backupCount=backupCount
        )
        self.formatter = logging.Formatter(
            "%(asctime)s, %(msecs)d %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.enable()
        self.logger.info("Started process.")

    def disable(self):
        self._enabled = False

    def enable(self):
        self._enabled = True

    def debug(self, msg, *args, **kwargs):
        if self._enabled:
            self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if self._enabled:
            self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if self._enabled:
            self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if self._enabled:
            self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        if self._enabled:
            self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        if self._enabled:
            self.logger.exception(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        if self._enabled:
            self.logger.log(level, msg, *args, **kwargs)

    def shutdown(self):
        self.disable()
        self.logger.info("shutting down")
        self.logger.handlers.clear()
