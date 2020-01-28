"""Lock files are created to prevent multiple people from grading an assignment simultaneously."""

import datetime
import getpass
import os

from .model import Student
from .model import Lab

from .. import config

def get_lock_files():
    """Return a list of all lock files"""
    return [l for l in os.listdir(config.zygrader.CLASS_DIRECTORY) if l.endswith(".lock")]

def get_lock_log_path():
    """Return path to lock log file"""
    return os.path.join(config.zygrader.CLASS_DIRECTORY, "locks_log.csv")

def log(name, lab, lock="LOCK"):
    """Logging utility for lock files

    This logs when each lab is locked and unlocked,
    along with when and by whom.
    """

    lock_log = get_lock_log_path()
    # Get timestamp
    timestamp = datetime.datetime.now().isoformat()

    line = f"{timestamp},{name},{lab},{getpass.getuser()},{lock}\n"
    with open(lock_log, 'a') as _log:
        _log.write(line)

def is_lab_locked(student: Student, lab: Lab):
    """Check if a submission is locked for a given student and lab"""
    # Try to match this against all the lock files in the directory
    lock_path_end = f"{lab.parts[0]['id']}.{student.id}.lock"

    for lock in get_lock_files():
        # Strip off username
        lock = ".".join(lock.split(".")[1:])

        if lock == lock_path_end:
            return True

    return False

def get_locked_netid(student: Student, lab: Lab):
    """Return netid of locked submission"""
    # Try to match this against all the lock files in the directory
    lock_path_end = f"{lab.parts[0]['id']}.{student.id}.lock"

    for lock in get_lock_files():
        if lock.endswith(lock_path_end):
            return lock.split(".")[0]

    return ""

def get_lock_file_path(student: Student, lab: Lab):
    """Return path for lock file"""
    username = getpass.getuser()

    # Get the lab and student names without spaces
    lab_name = "".join(lab.name.split())
    student_name = "".join(student.full_name.split())

    lock_path = f"{username}.{lab_name}.{student_name}.lock"
    return os.path.join(config.zygrader.CLASS_DIRECTORY, lock_path)

def lock_lab(student: Student, lab: Lab):
    """Lock the submission for the given student and lab

    Locking is done by creating a file with of the following format:
        username.lab.student.lock
    Where username is the grader's username.
    These files are used to determine if a submission is being graded.
    """
    lock = get_lock_file_path(student, lab)

    open(lock, 'w').close()

    log(student.full_name, lab.name)

def unlock_lab(student: Student, lab: Lab):
    """Unlock the submission for the given student and lab"""
    lock = get_lock_file_path(student, lab)

    # Only remove the lock if it exists
    if os.path.exists(lock):
        os.remove(lock)

    log(student.full_name, lab.name, "UNLOCK")

def unlock_all_labs_by_grader(username: str):
    """Remove all lock files for a given grader"""
    # Look at all lock files
    for lock in get_lock_files():
        lock_parts = lock.split(".")

        # Only look at the lock files graded by the current grader
        if lock_parts[0] == username:
            os.remove(os.path.join(config.zygrader.CLASS_DIRECTORY, lock))

def unlock_all_labs():
    """Remove all locks"""
    for lock in get_lock_files():
        os.remove(os.path.join(config.zygrader.CLASS_DIRECTORY, lock))

def remove_lock_file(_file):
    """Remove a specific lock file (not logged)"""
    locks_directory = config.zygrader.CLASS_DIRECTORY

    os.remove(os.path.join(locks_directory, _file))
