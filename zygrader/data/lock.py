"""Lock files are created to prevent multiple people from grading an assignment simultaneously."""

import csv
import datetime
import getpass
import os

from zygrader import logger
from zygrader.config.shared import SharedData

from .model import Lab, Student


def get_lock_files():
    """Return a list of all lock files"""
    return [
        l for l in os.listdir(SharedData.get_locks_directory())
        if l.endswith(".lock")
    ]


def get_lock_log_path():
    """Return path to lock log file"""
    return os.path.join(SharedData.get_logs_directory(), "locks_log.csv")


def log(name, lab, event_type, lock="LOCK"):
    """Logging utility for lock files

    This logs when each lab is locked and unlocked,
    along with when and by whom.
    This also logs to the shared log file
    """

    lock_log = get_lock_log_path()
    # Get timestamp
    timestamp = datetime.datetime.now().isoformat()

    with open(lock_log, "a", newline='') as _log:
        # Use csv to properly write names with commas in them
        csv.writer(_log).writerow(
            [timestamp, event_type, name, lab,
             getpass.getuser(), lock])

    logger.log(f"{name},{lab},{lock},{event_type}")


def get_lock_file_path(student: Student, lab: Lab = None):
    """Return path for lock file"""
    username = getpass.getuser()

    # We can safely store both lab+student and lab locks in the
    # Same directory
    if lab:
        lab_name = lab.get_unique_name()
        student_name = student.get_unique_name()
        lock_path = f"{username}.{lab_name}.{student_name}.lock"
    else:
        student_name = student.get_unique_name()
        lock_path = f"{username}.{student_name}.lock"

    return os.path.join(SharedData.get_locks_directory(), lock_path)


def is_locked(student: Student, lab: Lab = None):
    """Check if a submission is locked for a given student and lab"""
    # Try to match this against all the lock files in the directory
    lock_path = os.path.basename(get_lock_file_path(student, lab))
    lock_path_end = ".".join(lock_path.split(".")[1:])

    for lock in get_lock_files():
        # Strip off username
        lock = ".".join(lock.split(".")[1:])

        if lock == lock_path_end:
            return True

    return False


def get_locked_netid(student: Student, lab: Lab = None):
    """Return netid of locked submission"""
    # Try to match this against all the lock files in the directory
    lock_path = os.path.basename(get_lock_file_path(student, lab))
    lock_path_end = ".".join(lock_path.split(".")[1:])

    for lock in get_lock_files():
        if lock.endswith(lock_path_end):
            return lock.split(".")[0]

    return ""


def lock(student: Student, lab: Lab = None):
    """Lock the submission for the given student (and lab if given)

    Locking is done by creating a file with of the following format:
        username.lab.student.lock
    Where username is the grader's username.
    These files are used to determine if a submission is being graded.
    """
    lock = get_lock_file_path(student, lab)

    open(lock, "w").close()

    if lab:
        log(student.full_name, lab.name, "LAB")
    else:
        log(student.full_name, "N/A", "EMAIL")


def unlock(student: Student, lab: Lab = None):
    """Unlock the submission for the given student and lab"""
    lock = get_lock_file_path(student, lab)

    # Only remove the lock if it exists
    if os.path.exists(lock):
        os.remove(lock)
    if lab:
        log(student.full_name, lab.name, "LAB", "UNLOCK")
    else:
        log(student.full_name, "N/A", "EMAIL", "UNLOCK")


def unlock_all_labs_by_grader(username: str):
    """Remove all lock files for a given grader"""
    # Look at all lock files
    for lock in get_lock_files():
        lock_parts = lock.split(".")

        # Only look at the lock files graded by the current grader
        if lock_parts[0] == username:
            os.remove(os.path.join(SharedData.get_locks_directory(), lock))

    logger.log("All locks under the current grader were removed",
               logger.WARNING)


def unlock_all_labs():
    """Remove all locks"""
    for lock in get_lock_files():
        os.remove(os.path.join(SharedData.get_locks_directory(), lock))


def remove_lock_file(_file):
    """Remove a specific lock file (not logged to locks_log.csv)"""
    locks_directory = SharedData.get_locks_directory()

    os.remove(os.path.join(locks_directory, _file))

    logger.log("lock file was removed manually", _file, logger.WARNING)
