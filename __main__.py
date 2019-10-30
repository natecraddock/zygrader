import getpass
import signal
import sys

from zygrader import zygrade
from zygrader.data import lock

def lock_cleanup(signum, frame):
    lock.unlock_all_labs_by_grader(getpass.getuser())
    sys.exit(0)

# Handle Signals
signal.signal(signal.SIGTERM, lock_cleanup)
signal.signal(signal.SIGHUP, lock_cleanup)

zygrade.start()
