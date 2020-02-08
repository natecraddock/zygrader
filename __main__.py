#!/usr/bin/env python3
import curses
import getpass
import signal
import sys
import os

from zygrader import zygrader
from zygrader import config
from zygrader.data import lock
from zygrader import logger
from zygrader import ui

def lock_cleanup(signum, frame):
    lock.unlock_all_labs_by_grader(getpass.getuser())

def sigint_handler(signum, frame):
    if config.g_data.RUNNING_CODE:
        # If child process is running
        if config.g_data.running_process.poll() is None:
            config.g_data.RUNNING_CODE = False
            config.g_data.running_process.send_signal(signal.SIGINT)
            config.g_data.running_process = None
    else:
        lock_cleanup(None, None)
        sys.exit(0)

def sigtstp_handler(signum, frame):
    if config.g_data.RUNNING_CODE:
        # If child process is running
        if config.g_data.running_process.poll() is None:
            config.g_data.RUNNING_CODE = False
            config.g_data.running_process.send_signal(signal.SIGTSTP)

# Handle Signals
signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTSTP, sigtstp_handler)
# signal.signal(signal.SIGHUP, lock_cleanup)

# Ensure zygrader starts in the proper directory (one level up from the __main__.py file)
zygrader_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(zygrader_path)
os.chdir("..")

zygrader.start()

logger.log("zygrader exited normally")
