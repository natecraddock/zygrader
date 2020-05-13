import datetime
import json

from .ui.window import Window
from .ui import UI_GO_BACK
from .zybooks import Zybooks
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

    out_path = config.g_data.get_student_data()
    with open(out_path, 'w') as _file:
        json.dump(students, _file, indent=2)

def setup_new_class():
    window = Window.get_window()
    zy_api = Zybooks()
    
    code = window.create_text_input("Enter class code")
    if code == Window.CANCEL:
        return

    # Check if class code is valid
    valid = zy_api.check_valid_class(code)
    if valid:
        window.create_popup("Valid", [f"{code} is valid"])
    else:
        window.create_popup("Invalid", [f"{code} is invalid"])
        return

    # If code is valid, add it to the global configuration
    config.g_data.add_class(code)

    # Download the list of students
    roster = zy_api.get_roster()

    save_roster(roster)
    window.create_popup("Finished", ["Successfully downloaded student roster"])

def add_lab():
    window = Window.get_window()
    zy_api = Zybooks()

    lab_name = window.create_text_input("Lab Name")
    if lab_name == Window.CANCEL:
        return

    # Get lab part(s)
    parts = []
    number = window.create_text_input("Enter Chapter.section, e.g. 2.26 (ESC to cancel)")

    while number != Window.CANCEL:
        part = {}
        chapter, section = number.split(".")

        response = zy_api.get_zybook_section(chapter, section)
        if not response.success:
            window.create_popup("Error", ["Invalid URL"])
            continue

        # Name lab part and add to list of parts
        name = window.create_text_input("Edit part name")
        if name == Window.CANCEL:
            name = response.name

        part["name"] = name
        part["id"] = response.id
        parts.append(part)

        # Get next part
        number = window.create_text_input("Enter Chapter.section, e.g. 2.26 (ESC to finish)")

    new_lab = data.model.Lab(lab_name, parts, {})

    all_labs = data.get_labs()
    all_labs.append(new_lab)

    data.write_labs(all_labs)

def set_due_date(lab):
    window = Window.get_window()

    labs = data.get_labs()

    old_date = ""
    if "due" in lab.options:
        old_date = lab.options["due"].strftime("%m.%d.%Y:%H.%M.%S")

    due_date = window.create_text_input("Enter due date [MM.DD.YYYY:HH.MM.SS]", text=old_date)
    if due_date == Window.CANCEL:
        return

    # Clearing the due date
    if due_date == "" and "due" in lab.options:
        del lab.options["due"]
    else:
        lab.options["due"] = datetime.datetime.strptime(due_date, "%m.%d.%Y:%H.%M.%S").astimezone(tz=None)

    data.write_labs(labs)

# Toggle a boolean lab option (T/F value)
def toggle_lab_option(lab, option):
    if option in lab.options:
        del lab.options[option]
    else:
        lab.options[option] = ""

    labs = data.get_labs()
    data.write_labs(labs)

def rename_lab(lab):
    window = Window.get_window()

    labs = data.get_labs()

    name = window.create_text_input("Enter Lab's new name", text=lab.name)
    if name != Window.CANCEL:
        lab.name = name
        data.write_labs(labs)

edit_options = {"highest_score": "Grade Highest Scoring Submission",
                "diff_parts": "Diff Submission Parts",
                "due": None,
                }

def edit_lab_options_draw(lab):
    list = []
    for pref, name in edit_options.items():
        if not name:
            continue

        if pref in lab.options:
            list.append(f"[X] {name}")
        else:
            list.append(f"[ ] {name}")

    # Handle due date separately
    if "due" in lab.options:
        due_date = lab.options['due'].strftime("%m.%d.%Y:%H.%M.%S")
        list.append(f"    Due Date: {due_date}")
    else:
        list.append(f"    Due Date: None")

    return list

def edit_lab_options_callback(lab, selected_index):
    option = list(edit_options.keys())[selected_index]

    if option in {"highest_score", "diff_parts"}:
        toggle_lab_option(lab, option)
    elif option == "due":
        set_due_date(lab)

def edit_lab_options(lab):
    window = Window.get_window()

    draw = lambda : edit_lab_options_draw(lab)
    callback = lambda index : edit_lab_options_callback(lab, index)
    window.create_list_popup("Editing Lab Options", callback=callback, list_fill=draw)

def move_lab(lab, step):
    labs = data.get_labs()
    index = labs.index(lab)
    labs[index] = labs[index + step]
    labs[index + step] = lab

    data.write_labs(labs)

def edit_labs_callback(lab):
    window = Window.get_window()

    options = ["Remove", "Move Up", "Move Down", "Edit Options", "Done"]
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

    elif option == "Edit Options":
        edit_lab_options(lab)

def edit_labs():
    window = Window.get_window()
    labs = data.get_labs()

    while True:
        lab_index = window.create_filtered_list("Lab", input_data=labs)
        if lab_index is UI_GO_BACK:
            break

        edit_labs_callback(labs[lab_index])

def download_roster():
    window = Window.get_window()
    zy_api = Zybooks()

    roster = zy_api.get_roster()
    if not roster:
        window.create_popup("Failed", ["Failed to download student roster"])
        return

    save_roster(roster)
    window.create_popup("Finished", ["Successfully downloaded student roster"])

def change_class():
    window = Window.get_window()
    class_codes = config.g_data.get_class_codes()

    code_index = window.create_filtered_list("Class", input_data=class_codes)
    if code_index != UI_GO_BACK:
        config.g_data.set_current_class_code(class_codes[code_index])

        window.create_popup("Changed Class", [f"Class changed to {class_codes[code_index]}"])

class_manager_options = ["Setup New Class", "Add Lab", "Edit Labs", "Download Student Roster", "Change Class"]

def class_manager_callback(option_index):
    option = class_manager_options[option_index]

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
    window.set_header("Class Manager")

    window.create_filtered_list("Option", input_data=class_manager_options, callback=class_manager_callback)
