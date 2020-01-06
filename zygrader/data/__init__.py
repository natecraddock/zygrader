import json
import os

from .model import Student
from .model import Lab
from .model import Submission

from . import lock
from .. import config

g_students = []
g_labs = []

# Load students from JSON file
def get_students() -> list:
    if g_students:
        return g_students

    path = config.zygrader.STUDENT_DATA
    if not os.path.exists(path):
        return []

    with open(path, 'r') as students_file:
        students_json = json.load(students_file)
    
    for student in students_json:
        g_students.append(Student(student["first_name"], student["last_name"], student["email"], student["section"], student["id"]))

    return g_students

# Load labs from JSON file
def get_labs() -> list:
    if g_labs:
        return g_labs

    path = config.zygrader.LABS_DATA
    if not os.path.exists(path):
        return []

    with open(path, 'r') as labs_file:
        labs_json = json.load(labs_file)
    
    for a in labs_json:
        g_labs.append(Lab(a["name"], a["parts"], a["options"]))

    return g_labs

def write_labs(labs):
    g_labs = labs

    labs_json = []

    for lab in labs:
        labs_json.append(lab.to_json())

    path = config.zygrader.LABS_DATA
    with open(path, 'w') as _file:
        json.dump(labs_json, _file, indent=2)
