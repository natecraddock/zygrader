import json
import os

from zygrader.config.shared import SharedData

from . import flags, fs_watch, lock
from .model import ClassSection, Lab, Student, TA


def load_students() -> list:
    SharedData.STUDENTS.clear()
    path = SharedData.get_student_data()
    if not os.path.exists(path):
        return []

    with open(path, "r") as students_file:
        try:
            students_json = json.load(students_file)
        except json.decoder.JSONDecodeError:
            students_json = []

    for student in students_json:
        SharedData.STUDENTS.append(
            Student(
                student["first_name"],
                student["last_name"],
                student["email"],
                student["section"],
                student["id"],
            ))

    return SharedData.STUDENTS


# Load students from JSON file
def get_students() -> list:
    if SharedData.STUDENTS:
        return SharedData.STUDENTS

    return load_students()


def load_labs() -> list:
    SharedData.LABS.clear()
    path = SharedData.get_labs_data()
    if not os.path.exists(path):
        return []

    with open(path, "r") as labs_file:
        labs_json = json.load(labs_file)

    for a in labs_json:
        SharedData.LABS.append(Lab(a["name"], a["parts"], a["options"]))

    return SharedData.LABS


# Load labs from JSON file
def get_labs() -> list:
    if SharedData.LABS:
        return SharedData.LABS

    return load_labs()


def write_labs(labs):
    SharedData.LABS = labs

    labs_json = []

    for lab in labs:
        labs_json.append(lab.to_json())

    path = SharedData.get_labs_data()
    with open(path, "w") as _file:
        json.dump(labs_json, _file, indent=2)


# Load class sections from JSON file
def load_class_sections() -> list:
    SharedData.CLASS_SECTIONS.clear()
    path = SharedData.get_class_sections_data()
    if not os.path.exists(path):
        return []

    with open(path, "r") as class_sections_file:
        class_sections_json = json.load(class_sections_file)

    for class_section in class_sections_json:
        SharedData.CLASS_SECTIONS.append(ClassSection.from_json(class_section))

    return SharedData.CLASS_SECTIONS


def get_class_sections() -> list:
    if SharedData.CLASS_SECTIONS:
        return SharedData.CLASS_SECTIONS

    return load_class_sections()


def get_class_sections_in_ordered_list() -> list:
    unordered = get_class_sections()

    largest_section = max([section.section_number for section in unordered])

    ordered = [None] * (largest_section + 1)
    for section in unordered:
        ordered[section.section_number] = section

    return ordered


def write_class_sections(class_sections):
    SharedData.CLASS_SECTIONS = class_sections

    class_sections_json = []

    for class_section in class_sections:
        class_sections_json.append(class_section.to_json())

    path = SharedData.get_class_sections_data()
    with open(path, "w") as _file:
        json.dump(class_sections_json, _file, indent=2)


def load_tas() -> list:
    SharedData.TAS.clear()
    path = SharedData.get_ta_data()
    if not os.path.exists(path):
        return []

    with open(path, "r") as tas_file:
        tas_json = json.load(tas_file)

    for ta in tas_json:
        SharedData.TAS.append(TA.from_json(ta))

    return SharedData.TAS


def get_tas() -> list:
    if SharedData.TAS:
        return SharedData.TAS

    return load_tas()


def write_tas(tas):
    SharedData.TAS = tas

    tas_json = []

    for ta in tas:
        tas_json.append(ta.to_json())

    path = SharedData.get_ta_data()
    with open(path, "w") as _file:
        json.dump(tas_json, _file, indent=2)