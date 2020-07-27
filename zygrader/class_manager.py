"""Class Manager: Functions to manage zybooks classes"""
import datetime
import json

from zygrader.ui.window import WinContext, Window
from zygrader.ui.components import FilteredList, DatetimeSpinner
from zygrader.ui import UI_GO_BACK
from zygrader.zybooks import Zybooks
from zygrader import data
from zygrader.config.shared import SharedData

def save_roster(roster):
    """Save the roster of students to a json file"""
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

    out_path = SharedData.get_student_data()
    with open(out_path, 'w') as _file:
        json.dump(students, _file, indent=2)

def setup_new_class():
    """Setup a new class based on a zyBooks class code"""
    window = Window.get_window()
    zy_api = Zybooks()

    code = window.create_text_input("Class Code", "Enter class code")
    if code == Window.CANCEL:
        return

    # Check if class code is valid
    valid = zy_api.check_valid_class(code)
    if valid:
        window.create_popup("Valid", [f"{code} is valid"])
    else:
        window.create_popup("Invalid", [f"{code} is invalid"])
        return

    # If code is valid, add it to the shared configuration
    SharedData.add_class(code)

    # Download the list of students
    roster = zy_api.get_roster()

    save_roster(roster)
    window.create_popup("Finished", ["Successfully downloaded student roster"])

def add_lab():
    """Add a lab to the current class"""
    window = Window.get_window()
    zy_api = Zybooks()

    lab_name = window.create_text_input("Lab Name", "Enter the Lab Name")
    if lab_name == Window.CANCEL:
        return

    # Get lab part(s)
    parts = []
    number = window.create_text_input("Enter Part", "Enter Chapter.section, e.g. 2.26 (ESC to cancel)")

    while number != Window.CANCEL:
        part = {}
        chapter, section = number.split(".")

        response = zy_api.get_zybook_section(chapter, section)
        if not response.success:
            window.create_popup("Error", ["Invalid URL"])
        else:
            # Name lab part and add to list of parts
            name = window.create_text_input("Part Name", "Enter new part name")
            if name == Window.CANCEL:
                name = response.name

            part["name"] = name
            part["id"] = response.id
            parts.append(part)

        # Get next part
        number = window.create_text_input("Enter Part", "Enter Chapter.section, e.g. 2.26 (ESC to finish)")

    new_lab = data.model.Lab(lab_name, parts, {})

    all_labs = data.get_labs()
    all_labs.append(new_lab)

    data.write_labs(all_labs)

def set_due_date(lab):
    """Set a cutoff date for a lab

    When grading the submission before the cutoff date will be shown, but the
    in-grader submission picker allows to pick submissions after the cutoff date
    if needed
    """
    window = Window.get_window()

    labs = data.get_labs()

    old_date = None
    if "due" in lab.options:
        old_date = lab.options["due"]

    due_date = window.create_datetime_spinner("Due Date", time=old_date if old_date else None, optional=True)
    if due_date == UI_GO_BACK:
        return

    # Clearing the due date
    if due_date == DatetimeSpinner.NO_DATE:
        if  "due" in lab.options:
            del lab.options["due"]
    else:
        # Remove time zone information
        lab.options["due"] = due_date.astimezone(tz=None)

    data.write_labs(labs)

def toggle_lab_option(lab, option):
    """Toggle a boolean lab option (T/F value)"""
    if option in lab.options:
        del lab.options[option]
    else:
        lab.options[option] = ""

    labs = data.get_labs()
    data.write_labs(labs)

def rename_lab(filtered_list, lab):
    """Rename a lab"""
    window = Window.get_window()

    labs = data.get_labs()

    name = window.create_text_input("Rename Lab", "Enter Lab's new name", text=lab.name)
    if name != Window.CANCEL:
        lab.name = name
        data.write_labs(labs)
        filtered_list.refresh()

EDIT_OPTIONS = {"highest_score": "Grade Highest Scoring Submission",
                "diff_parts": "Diff Submission Parts",
                "due": None,
                }

def edit_lab_options_draw(lab):
    """Callback to draw the list of lab edit options"""
    options = []
    for pref, name in EDIT_OPTIONS.items():
        if not name:
            continue

        if pref in lab.options:
            options.append(f"[X] {name}")
        else:
            options.append(f"[ ] {name}")

    # Handle due date separately
    if "due" in lab.options:
        due_date = lab.options['due'].strftime("%m.%d.%Y:%H.%M.%S")
        options.append(f"    Due Date: {due_date}")
    else:
        options.append(f"    Due Date: None")

    return options

def edit_lab_options_callback(lab, selected_index):
    """Callback to run when an edit lab option is chosen"""
    option = list(EDIT_OPTIONS.keys())[selected_index]

    if option in {"highest_score", "diff_parts"}:
        toggle_lab_option(lab, option)
    elif option == "due":
        set_due_date(lab)

def edit_lab_options(lab):
    """Create a popup listing the options in EDIT_OPTIONS"""
    window = Window.get_window()

    draw = lambda: edit_lab_options_draw(lab)
    callback = lambda context: edit_lab_options_callback(lab, context.data)
    window.create_list_popup("Editing Lab Options", callback=callback, list_fill=draw)

def move_lab(filtered_list, lab, step):
    """Move a lab up or down the list of labs"""
    labs = data.get_labs()
    index = labs.index(lab)

    # Prevent moving out of bounds
    if index + step > len(labs) - 1 or index + step < 0:
        return

    labs[index] = labs[index + step]
    labs[index + step] = lab

    data.write_labs(labs)
    filtered_list.refresh()
    filtered_list.selected_index += step

def remove_fn(filtered_list, window, lab) -> bool:
    """Remove a lab from the list"""
    msg = [f"Are you sure you want to remove {lab.name}?"]
    remove = window.create_bool_popup("Confirm", msg)

    if remove:
        labs = data.get_labs()
        labs.remove(lab)
        data.write_labs(labs)

    filtered_list.refresh()
    return remove

def edit_labs_callback(lab, filtered_list):
    """Create a popup for basic lab editing options"""
    window = Window.get_window()

    options = {
        "Remove": lambda _: remove_fn(filtered_list, window, lab),
        "Rename": lambda _: rename_lab(filtered_list, lab),
        "Move Up": lambda _: move_lab(filtered_list, lab, -1),
        "Move Down": lambda _: move_lab(filtered_list, lab, 1),
        "Edit Options": lambda _: edit_lab_options(lab)
    }

    msg = [f"Editing {lab.name}", "", "Select an option"]
    window.create_options_popup("Edit Lab", msg, options)

def draw_lab_list() -> list:
    """Use a callback for drawing the filtered list of labs so it can be refreshed"""
    labs = data.get_labs()
    return [FilteredList.ListLine(i, lab) for i, lab in enumerate(labs, start=1)]

def edit_labs():
    """Creates a list of labs to edit"""
    window = Window.get_window()

    edit_fn = lambda context: edit_labs_callback(data.get_labs()[context.data], context.component)
    window.create_filtered_list("Lab", list_fill=draw_lab_list, callback=edit_fn)

def download_roster(silent=False):
    """Download the roster of students from zybooks and save to disk"""
    window = Window.get_window()
    zy_api = Zybooks()

    roster = zy_api.get_roster()

    if not silent and not roster:
        window.create_popup("Failed", ["Failed to download student roster"])
        return

    save_roster(roster)
    if not silent:
        window.create_popup("Finished", ["Successfully downloaded student roster"])

def change_class():
    """Change the current class.

    This applies globally to all users of zygrader.
    """
    window = Window.get_window()
    class_codes = SharedData.get_class_codes()

    code_index = window.create_filtered_list("Class", input_data=class_codes)
    if code_index != UI_GO_BACK:
        SharedData.set_current_class_code(class_codes[code_index])

        window.create_popup("Changed Class", [f"Class changed to {class_codes[code_index]}"])

CLASS_MANAGE_OPTIONS = ["Setup New Class", "Add Lab", "Edit Labs",
                        "Download Student Roster", "Change Class"]

def class_manager_callback(context: WinContext):
    """Run the function for each option in CLASS_MANAGE_OPTIONS"""
    option_index = context.data
    option = CLASS_MANAGE_OPTIONS[option_index]

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
    """Create the main class manager menu"""
    window = Window.get_window()
    window.set_header("Class Manager")

    window.create_filtered_list("Option", input_data=CLASS_MANAGE_OPTIONS,
                                callback=class_manager_callback)
