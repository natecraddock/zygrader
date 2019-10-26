import os
import pickle

from .model import Student
from .model import Lab

from .. import config

def create_database(labs):
    db = {}

    for lab in labs:
        db[lab.name] = []
    
    with open(config.zygrader.DATABASE, 'wb') as db_file:
        pickle.dump(db, db_file)

def open_database(write):
    # Ensure that we are the only ones writing to the database
    while is_database_locked():
        pass
    
    # Immediately lock the database if writing
    if write:
        lock_database()

    with open(config.zygrader.DATABASE, 'rb') as db_file:
        return pickle.load(db_file)

def write_database(db):
    with open(config.zygrader.DATABASE, 'wb') as db_file:
        pickle.dump(db, db_file)
    
    # Unlock the database
    unlock_database()

def lock_database():
    open(f"{config.zygrader.DATABASE}.lock", 'w').close()

def unlock_database():
    os.remove(f"{config.zygrader.DATABASE}.lock")

def is_database_locked():
    return os.path.exists(f"{config.zygrader.DATABASE}.lock")

def init_database(labs):
    if not os.path.exists(config.zygrader.DATABASE):
        create_database(labs)

def is_lab_locked(student: Student, lab: Lab):
    db = open_database(False)

    return student.id in db[lab.name]

def lock_lab(student: Student, lab: Lab):
    db = open_database(True)

    db[lab.name].append(student.id)

    write_database(db)

def unlock_lab(student: Student, lab: Lab):
    db = open_database(True)

    db[lab.name].remove(student.id)

    write_database(db)