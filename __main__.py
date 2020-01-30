import getpass
import signal
import sys

from zygrader import zygrader
from zygrader.data import lock
from zygrader import logger

def lock_cleanup(signum, frame):
    lock.unlock_all_labs_by_grader(getpass.getuser())
    sys.exit(0)

# Handle Signals
signal.signal(signal.SIGINT, lock_cleanup)
# signal.signal(signal.SIGHUP, lock_cleanup)

zygrader.start()

logger.log("zygrader exited normally")
