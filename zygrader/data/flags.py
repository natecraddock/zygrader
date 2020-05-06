"""Flags are used to leave a note on a submission that shouldn't be graded yet
   This is similar in concept to locks but don't require username info.

   Also each flag file is a text file that stores a brief note.
"""

import os

from .model import Student
from .model import Lab

from .. import config
from ..ui.window import Window

def get_flag_files():
    """Return a list of all flag files"""
    return [f for f in os.listdir(config.g_data.get_flags_directory())]

def get_flag_file_path(student: Student, lab: Lab):
    """Return path for a unique flag file given a student and lab"""

    lab_name = lab.get_unique_name()
    student_name = student.get_unique_name()

    flag_path = f"{lab_name}.{student_name}.flag"
    return os.path.join(config.g_data.get_flags_directory(), flag_path)

def is_submission_flagged(student: Student, lab: Lab):
    """Checks if a given submission is flagged"""
    flag_path = get_flag_file_path(student, lab)
    return os.path.exists(flag_path)

def get_flag_message(student: Student, lab: Lab):
    """Return the string stored in a flag"""
    flag_path = get_flag_file_path(student, lab)

    with open(flag_path, 'r') as _file:
        string = _file.read()

    return string

def flag_submission(student: Student, lab: Lab, string: str):
    """Create a flag file containing a given string for a given submission"""
    flag_path = get_flag_file_path(student, lab)

    with open(flag_path, 'w') as _file:
        _file.write(string)

def unflag_submission(student: Student, lab: Lab):
    """Remove a flag file for a given submission"""
    flag_path = get_flag_file_path(student, lab)

    if os.path.exists(flag_path):
        os.remove(flag_path)
