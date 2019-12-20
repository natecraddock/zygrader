import os
import json

from .ui.window import Window
from .zyscrape import Zyscrape
from . import data
from . import config

def save_roster(roster):
    roster = roster["roster"] # It is stored under "roster" in the json

    # Download students (and others)
    students = []
    for role in roster:
        for person in roster[role]:
            student = {}
            student["first_name"] = person["first_name"]
            student["last_name"] = person["last_name"]
            student["email"] = person["primary_email"]
            student["id"] = person["user_id"]

            if "class_section" in person:
                student["section"] = person["class_section"]["value"]
            else:
                student["section"] = -1

            students.append(student)

    out_path = config.zygrader.STUDENT_DATA
    with open(out_path, 'w') as _file:
        json.dump(students, _file, indent=2)

def setup_new_class():
    window = Window.get_window()
    scraper = Zyscrape()
    
    code = window.text_input("Enter class code")

    # Check if class code is valid
    valid = scraper.check_valid_class(code)
    if valid:
        window.create_popup("Valid", [f"{code} is valid"])
    else:
        window.create_popup("Invalid", [f"{code} is invalid"])
        return

    # If code is valid, add it to the global configuration
    config.zygrader.add_class(code)

    # Download the list of students
    roster = scraper.get_roster()

    save_roster(roster)
    window.create_popup("Finished", ["Successfully downloaded student roster"])

def download_roster():
    window = Window.get_window()
    scraper = Zyscrape()

    roster = scraper.get_roster()
    if not roster:
        window.create_popup("Failed", ["Failed to download student roster"])
        return

    save_roster(roster)
    window.create_popup("Finished", ["Successfully downloaded student roster"])

def change_class():
    window = Window.get_window()
    class_codes = config.zygrader.get_class_codes()

    code = window.filtered_list(class_codes, "Class")
    if code != 0:
        config.zygrader.set_current_class_code(code)

        window.create_popup("Changed Class", [f"Class changed to {code}"])

def class_manager_callback(option):
    if option == "Setup New Class":
        setup_new_class()
    if option == "Change Class":
        change_class()
    elif option == "Download Student Roster":
        download_roster()

def start():
    window = Window.get_window()

    options = ["Setup New Class", "Download Student Roster", "Change Class"]

    window.filtered_list(options, "Option", callback=class_manager_callback)
