import datetime
import getpass
import os

from .model import Student
from .model import Lab

from .. import config

def get_lock_files():
    return [l for l in os.listdir(config.zygrader.CLASS_DIRECTORY) if l.endswith(".lock")]

def get_lock_log_path():
    return os.path.join(config.zygrader.CLASS_DIRECTORY, "locks_log.csv")

def log(name, lab, lock="LOCK"):
    lock_log = get_lock_log_path()
    # Get timestamp
    timestamp = datetime.datetime.now().isoformat()

    line = f"{timestamp},{name},{lab},{getpass.getuser()},{lock}\n"
    with open(lock_log, 'a') as _log:
        _log.write(line);

def is_lab_locked(student: Student, lab: Lab):
    # Try to match this against all the lock files in the directory
    lock_path_end = f"{lab.parts[0]['id']}.{student.id}.lock"

    for lock in get_lock_files():
        # Strip off username
        lock = ".".join(lock.split(".")[1:])

        if lock == lock_path_end:
            return True

    return False

def get_locked_netid(student: Student, lab: Lab):
    # Try to match this against all the lock files in the directory
    lock_path_end = f"{lab.parts[0]['id']}.{student.id}.lock"

    for lock in get_lock_files():
        if lock.endswith(lock_path_end):
            return lock.split(".")[0]

    return ""

def get_lock_file_path(student: Student, lab: Lab):
    username = getpass.getuser()
    # Use the lab id of the first part (should be unique)
    lab_id = lab.parts[0]["id"]
    student_id = student.id

    lock_path = f"{username}.{lab_id}.{student_id}.lock"
    return os.path.join(config.zygrader.CLASS_DIRECTORY, lock_path)

def lock_lab(student: Student, lab: Lab):
    lock = get_lock_file_path(student, lab)

    open(lock, 'w').close()

    log(student.full_name, lab.name)

def unlock_lab(student: Student, lab: Lab):
    lock = get_lock_file_path(student, lab)

    # Only remove the lock if it exists
    if os.path.exists(lock):
        os.remove(lock)

    log(student.full_name, lab.name, "UNLOCK")

def unlock_all_labs_by_grader(username: str):
    # Look at all lock files
    for lock in get_lock_files():
        lock_parts = lock.split(".")

        # Only look at the lock files graded by the current grader
        if lock_parts[0] == username:
            os.remove(os.path.join(config.zygrader.CLASS_DIRECTORY, lock))

def unlock_all_labs():
    for lock in get_lock_files():
        os.remove(os.path.join(config.zygrader.CLASS_DIRECTORY, lock))

def remove_lock_file(_file):
    locks_directory = config.zygrader.CLASS_DIRECTORY

    os.remove(os.path.join(locks_directory, _file))
