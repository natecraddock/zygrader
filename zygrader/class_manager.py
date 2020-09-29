"""Class Manager: Functions to manage zybooks classes"""
import json

from zygrader.ui.templates import ZybookSectionSelector
from zygrader.zybooks import Zybooks
from zygrader import data
from zygrader import ui
from zygrader.config.shared import SharedData


def save_roster(roster):
    """Save the roster of students to a json file"""
    roster = roster["roster"]  # It is stored under "roster" in the json

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
    with open(out_path, "w") as _file:
        json.dump(students, _file, indent=2)


def setup_new_class():
    """Setup a new class based on a zyBooks class code"""
    window = ui.get_window()
    zy_api = Zybooks()

    code = window.create_text_input("Class Code", "Enter class code")
    if code == ui.Window.CANCEL:
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

    class_section_manager()


def add_lab():
    """Add a lab to the current class"""
    window = ui.get_window()
    zy_api = Zybooks()

    lab_name = window.create_text_input("Lab Name", "Enter the Lab Name")
    if lab_name == ui.Window.CANCEL:
        return

    # Get lab part(s)
    parts = []

    section_selector = ZybookSectionSelector(allow_optional_and_hidden=True)
    section_numbers = section_selector.select_zybook_sections(
        return_just_numbers=True)

    for chapter, section in section_numbers:
        part = {}
        response = zy_api.get_zybook_section(chapter, section)
        if not response.success:
            window.create_popup("Error", ["Invalid URL"])
        part["name"] = response.name
        part["id"] = response.id
        parts.append(part)

    new_lab = data.model.Lab(lab_name, parts, {})

    edit_lab_options(new_lab)

    all_labs = data.get_labs()
    all_labs.append(new_lab)

    data.write_labs(all_labs)


def set_due_date(lab):
    """Set a cutoff date for a lab

    When grading the submission before the cutoff date will be shown, but the
    in-grader submission picker allows to pick submissions after the cutoff date
    if needed
    """
    window = ui.get_window()

    labs = data.get_labs()

    old_date = None
    if "due" in lab.options:
        old_date = lab.options["due"]

    due_date = window.create_datetime_spinner(
        "Due Date", time=old_date if old_date else None, optional=True)
    if due_date == ui.GO_BACK:
        return

    # Clearing the due date
    if due_date == ui.components.DatetimeSpinner.NO_DATE:
        if "due" in lab.options:
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
    window = ui.get_window()

    labs = data.get_labs()

    name = window.create_text_input("Rename Lab",
                                    "Enter Lab's new name",
                                    text=lab.name)
    if name != ui.Window.CANCEL:
        lab.name = name
        data.write_labs(labs)
        filtered_list.refresh()


EDIT_OPTIONS = {
    "highest_score": "Grade Highest Scoring Submission",
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
        due_date = lab.options["due"].strftime("%m.%d.%Y:%H.%M.%S")
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
    window = ui.get_window()

    draw = lambda: edit_lab_options_draw(lab)
    callback = lambda context: edit_lab_options_callback(lab, context.data)
    window.create_list_popup("Editing Lab Options",
                             callback=callback,
                             list_fill=draw)


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
    window = ui.get_window()

    options = {
        "Remove": lambda _: remove_fn(filtered_list, window, lab),
        "Rename": lambda _: rename_lab(filtered_list, lab),
        "Move Up": lambda _: move_lab(filtered_list, lab, -1),
        "Move Down": lambda _: move_lab(filtered_list, lab, 1),
        "Edit Options": lambda _: edit_lab_options(lab),
    }

    msg = [f"Editing {lab.name}", "", "Select an option"]
    window.create_options_popup("Edit Lab", msg, options)


def draw_lab_list() -> list:
    """Use a callback for drawing the filtered list of labs so it can be refreshed"""
    labs = data.get_labs()
    return [
        ui.components.FilteredList.ListLine(i, lab)
        for i, lab in enumerate(labs, start=1)
    ]


def edit_labs():
    """Creates a list of labs to edit"""
    window = ui.get_window()

    edit_fn = lambda context: edit_labs_callback(data.get_labs()[context.data],
                                                 context.component)
    window.create_filtered_list("Lab",
                                list_fill=draw_lab_list,
                                callback=edit_fn)


def get_class_section(old_section: data.model.ClassSection = None):
    window = ui.get_window()

    init_text = ""
    if old_section:
        init_text = str(old_section.section_number)
    section_num_str = window.create_text_input(
        "Section Number",
        "Enter the new section number for this section",
        text=init_text)

    if section_num_str == ui.Window.CANCEL:
        return None

    section_num = int(section_num_str)

    default_due_time = window.create_datetime_spinner(
        "Section Default Due Time",
        quickpicks=[(50, 0), (59, 59), (0, 0)],
        include_date=False)

    if default_due_time == ui.GO_BACK:
        return None

    return data.model.ClassSection(section_num, default_due_time)


def add_class_section():
    """Add a class section to the current class"""
    new_class_section = get_class_section()
    if not new_class_section:
        return

    class_sections = data.get_class_sections()
    class_sections.append(new_class_section)

    data.write_class_sections(class_sections)


def edit_class_sections_callback(context: ui.WinContext):
    class_section = data.get_class_sections()[context.data]

    new_section = get_class_section(old_section=class_section)
    if not new_section:
        return

    class_section.copy(new_section)

    data.write_class_sections(data.get_class_sections())
    context.component.refresh()


def draw_class_section_list() -> list:
    """Use a callback for drawing the filtered list
    of class sections so it can be refreshed"""
    class_sections = data.get_class_sections()
    return [
        ui.components.FilteredList.ListLine(i, el)
        for i, el in enumerate(class_sections, start=1)
    ]


def edit_class_sections():
    """Create list of class sections to edit"""
    window = ui.get_window()

    window.create_filtered_list("Class Section",
                                list_fill=draw_class_section_list,
                                callback=edit_class_sections_callback)


def sort_class_sections():
    class_sections = data.get_class_sections()
    class_sections = sorted(class_sections, key=lambda sec: sec.section_number)
    data.write_class_sections(class_sections)

    window = ui.get_window()

    msg = ["The Class Sections are now sorted by section number"]
    window.create_popup("Finished", msg)


def download_roster(silent=False):
    """Download the roster of students from zybooks and save to disk"""
    window = ui.get_window()
    zy_api = Zybooks()

    roster = zy_api.get_roster()

    if not silent and not roster:
        window.create_popup("Failed", ["Failed to download student roster"])
        return
    if roster:
        save_roster(roster)
    if not silent:
        window.create_popup("Finished",
                            ["Successfully downloaded student roster"])


def change_class():
    """Change the current class.

    This applies globally to all users of zygrader.
    """
    window = ui.get_window()
    class_codes = SharedData.get_class_codes()

    code_index = window.create_filtered_list("Class", input_data=class_codes)
    if code_index != ui.GO_BACK:
        SharedData.set_current_class_code(class_codes[code_index])

        window.create_popup("Changed Class",
                            [f"Class changed to {class_codes[code_index]}"])


LAB_MANAGE_OPTIONS = ["Add Lab", "Edit Current Labs"]


def lab_manager_callback(context: ui.WinContext):
    option_index = context.data
    option = LAB_MANAGE_OPTIONS[option_index]

    if option == "Add Lab":
        add_lab()
    elif option == "Edit Current Labs":
        edit_labs()


def lab_manager():
    window = ui.get_window()
    window.set_header("Lab Manager")

    window.create_filtered_list("Option",
                                input_data=LAB_MANAGE_OPTIONS,
                                callback=lab_manager_callback)


CLASS_SECTION_MANAGE_OPTIONS = [
    "Add Section",
    "Edit Current Sections",
    "Sort Current Sections",
]


def class_section_manager_callback(context: ui.WinContext):
    option_index = context.data
    option = CLASS_SECTION_MANAGE_OPTIONS[option_index]

    if option == "Add Section":
        add_class_section()
    elif option == "Edit Current Sections":
        edit_class_sections()
    elif option == "Sort Current Sections":
        sort_class_sections()


def class_section_manager():
    window = ui.get_window()
    window.set_header("Class Section Manager")

    window.create_filtered_list("Option",
                                input_data=CLASS_SECTION_MANAGE_OPTIONS,
                                callback=class_section_manager_callback)


CLASS_MANAGE_OPTIONS = [
    "Setup New Class",
    "Lab Manager",
    "Class Section Manager",
    "Download Student Roster",
    "Change Class",
]


def class_manager_callback(context: ui.WinContext):
    """Run the function for each option in CLASS_MANAGE_OPTIONS"""
    option_index = context.data
    option = CLASS_MANAGE_OPTIONS[option_index]

    if option == "Setup New Class":
        setup_new_class()
    elif option == "Lab Manager":
        lab_manager()
    elif option == "Class Section Manager":
        class_section_manager()
    elif option == "Change Class":
        change_class()
    elif option == "Download Student Roster":
        download_roster()


def start():
    """Create the main class manager menu"""
    window = ui.get_window()
    window.set_header("Class Manager")

    window.create_filtered_list("Option",
                                input_data=CLASS_MANAGE_OPTIONS,
                                callback=class_manager_callback)
