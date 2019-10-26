import json

from .model import Student
from .model import Lab
from . import lock

# Load students from JSON file
def load_students(path):
    students = []
    with open(path, 'r') as students_file:
        students_json = json.load(students_file)
    
    for student in students_json:
        students.append(Student(student["first_name"], student["last_name"], student["email"], student["section"], student["id"]))

    return students

# Load assignments from JSON file
def load_assignments(path):
    assignments = []
    with open(path, 'r') as assignments_file:
        assignments_json = json.load(assignments_file)
    
    for a in assignments_json:
        assignments.append(Lab(a["name"], a["type"], a["parts"], a["options"]))

    return assignments
