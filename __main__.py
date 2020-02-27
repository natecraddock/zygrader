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

def lock_cleanup():
    lock.unlock_all_labs_by_grader(getpass.getuser())

def sighup_handler(signum, frame):
    lock_cleanup()

def sigint_handler(signum, frame):
    if config.g_data.RUNNING_CODE:
        # If child process is running
        if config.g_data.running_process.poll() is None:
            config.g_data.RUNNING_CODE = False
            config.g_data.running_process.send_signal(signal.SIGINT)
            config.g_data.running_process = None
    else:
        lock_cleanup()
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
signal.signal(signal.SIGHUP, sighup_handler)

# Ensure zygrader starts in the proper directory (one level up from the __main__.py file)
zygrader_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(zygrader_path)
os.chdir("..")

# Set a short ESC key delay (curses environment variable)
os.environ.setdefault('ESCDELAY', '25')

zygrader.start()

logger.log("zygrader exited normally")
