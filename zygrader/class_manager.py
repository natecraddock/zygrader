import os
import json

from .ui.window import Window
from .ui import components
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

def add_lab():
    window = Window.get_window()
    scraper = Zyscrape()

    lab_name = window.text_input("Lab Name")

    # Get lab part(s)
    parts = []
    number = window.text_input("Enter Chapter.section, e.g. 2.26 (enter \"done\" to finish)")
    while number != "done":
        part = {}
        chapter, section = number.split(".")

        response = scraper.get_zybook_section(chapter, section)
        if not response["success"]:
            window.create_popup("Error", ["Invalid URL"])
            continue

        part_id = response["id"]
        name = response["name"]

        # Name lab part and add to list of parts
        name = window.text_input("Edit part name")
        part["name"] = name
        part["id"] = part_id
        parts.append(part)

        # Get next part
        number = window.text_input("Enter Chapter.section, e.g. 2.26 (enter \"done\" to finish)")

    new_lab = data.model.Lab(lab_name, parts, {})

    all_labs = data.get_labs()
    all_labs.append(new_lab)

    data.write_labs(all_labs)

def set_due_date(lab):
    window = Window.get_window()

    labs = data.get_labs()

    old_date = ""
    if "due" in lab.options:
        old_date = lab.options["due"]

    due_date = window.text_input("Enter due date [MM.DD.YY:HH.MM.SS]", text=old_date)

    # Clearing the due date
    if due_date == "" and "due" in lab.options:
        del lab.options["due"]
    else:
        lab.options["due"] = due_date

    data.write_labs(labs)

def toggle_grade_highest_score(lab):
    if "highest_score" in lab.options:
        del lab.options["highest_score"]
    else:
        lab.options["highest_score"] = ""

    labs = data.get_labs()
    data.write_labs(labs)

# TODO: Abstract this
def toggle_part_diffing(lab):
    if "diff_parts" in lab.options:
        del lab.options["diff_parts"]
    else:
        lab.options["diff_parts"] = ""

    labs = data.get_labs()
    data.write_labs(labs)

def rename_lab(lab):
    window = Window.get_window()

    labs = data.get_labs()

    name = window.text_input("Enter Lab's new name", text=lab.name)

    lab.name = name
    data.write_labs(labs)

def edit_lab(lab):
    window = Window.get_window()

    while True:
        highest_score = " "
        date = " "
        diff_parts = " "
        due_date = ""
        if "highest_score" in lab.options:
            highest_score = "X"
        if "diff_parts" in lab.options:
            diff_parts = "X"
        if "due" in lab.options:
            date = "X"
            due_date = lab.options["due"]
        message = [f"Editing {lab.name}",
                   f"[{highest_score}] Grade Highest Scoring Submission",
                   f"[{diff_parts}] Diff Submission Parts",
                   f"[{date}] Due Date: {due_date}",
                   "",
                   "Due dates are formatted MM.DD.YY:HH.MM.SS. For example",
                   "November 15, 2019 at midnight is 11.15.2019:23.59.59"]

        options = ["Set Due Date", "Toggle Highest Score", "Toggle Part Diffing", "Rename", "Done"]

        option = window.create_options_popup("Edit Lab", message, options, align=components.Popup.ALIGN_LEFT)

        if option == "Done":
            break
        elif option == "Set Due Date":
            set_due_date(lab)
        elif option == "Toggle Highest Score":
            toggle_grade_highest_score(lab)
        elif option == "Toggle Part Diffing":
            toggle_part_diffing(lab)
        elif option == "Rename":
            rename_lab(lab)

def move_lab(lab, step):
    labs = data.get_labs()
    index = labs.index(lab)
    labs[index] = labs[index + step]
    labs[index + step] = lab

    data.write_labs(labs)

def edit_labs_callback(lab):
    window = Window.get_window()

    options = ["Remove", "Move Up", "Move Down", "Edit", "Done"]
    option = window.create_options_popup("Edit Lab", ["Select an option"], options)

    if option == "Remove":
        msg = [f"Are you sure you want to remove {lab.name}?"]
        remove = window.create_bool_popup("Confirm", msg)

        if remove:
            labs = data.get_labs()
            labs.remove(lab)
            data.write_labs(labs)

    elif option == "Move Up":
        move_lab(lab, -1)

    elif option == "Move Down":
        move_lab(lab, -1)

    elif option == "Edit":
        edit_lab(lab)

def edit_labs():
    window = Window.get_window()
    labs = data.get_labs()

    while True:
        lab = window.filtered_list(labs, "Lab")
        if lab is 0:
            break

        edit_labs_callback(lab)

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
    elif option == "Add Lab":
        add_lab()
    elif option == "Edit Labs":
        edit_labs()
    elif option == "Change Class":
        change_class()
    elif option == "Download Student Roster":
        download_roster()

def start():
    window = Window.get_window()

    options = ["Setup New Class", "Add Lab", "Edit Labs", "Download Student Roster", "Change Class"]

    window.filtered_list(options, "Option", callback=class_manager_callback)
