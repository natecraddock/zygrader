import json
import os

from .model import Student, Lab, ClassSection

from zygrader.config.shared import SharedData
from . import flags
from . import fs_watch
from . import lock

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


# Load class sections from JSON file
def load_class_sections() -> list:
    g_class_sections.clear()
    path = SharedData.get_class_sections_data()
    if not os.path.exists(path):
        return []

    with open(path, 'r') as class_sections_file:
        class_sections_json = json.load(class_sections_file)

    for class_section in class_sections_json:
        g_class_sections.append(ClassSection.from_json(class_section))

    return g_class_sections

def get_class_sections() -> list:
    if g_class_sections:
        return g_class_sections

    return load_class_sections()

def get_class_sections_in_ordered_list() -> list:
    unordered = get_class_sections()

    largest_section = max([section.section_number for section in unordered])

    ordered = [None] * (largest_section + 1)
    for section in unordered:
        ordered[section.section_number] = section

    return ordered

def write_class_sections(class_sections):
    global g_class_sections
    g_class_sections = class_sections

    class_sections_json = []

    for class_section in class_sections:
        class_sections_json.append(class_section.to_json())

    path = SharedData.get_class_sections_data()
    with open(path, 'w') as _file:
        json.dump(class_sections_json, _file, indent=2)