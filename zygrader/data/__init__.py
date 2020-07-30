import json
import os

from .model import Student
from .model import Lab
from .model import Submission

from zygrader.config.shared import SharedData
from . import flags
from . import fs_watch
from . import lock

g_students = []
g_labs = []

def load_students() -> list:
    g_students.clear()
    path = SharedData.get_student_data()
    if not os.path.exists(path):
        return []

    with open(path, 'r') as students_file:
        students_json = json.load(students_file)

    for student in students_json:
        g_students.append(Student(student["first_name"], student["last_name"], student["email"], student["section"], student["id"]))

    return g_students

# Load students from JSON file
def get_students() -> list:
    if g_students:
        return g_students

    return load_students()

def load_labs() -> list:
    g_labs.clear()
    path = SharedData.get_labs_data()
    if not os.path.exists(path):
        return []

    with open(path, 'r') as labs_file:
        labs_json = json.load(labs_file)

    for a in labs_json:
        g_labs.append(Lab(a["name"], a["parts"], a["options"]))

    return g_labs


# Load labs from JSON file
def get_labs() -> list:
    if g_labs:
        return g_labs

    return load_labs()

def write_labs(labs):
    global g_labs
    g_labs = labs

    labs_json = []

    for lab in labs:
        labs_json.append(lab.to_json())

    path = SharedData.get_labs_data()
    with open(path, 'w') as _file:
        json.dump(labs_json, _file, indent=2)
