import os
import sys

from . import data
from . import config
from . import grader

from .data import get_students, get_labs
from .data.model import Lab
from .data.model import Student

from .zyscrape import Zyscrape

from .ui import window
from .ui.window import Window
from .ui import components

def config_menu():
    window = Window.get_window()
    scraper = Zyscrape()
    config_file = config.user.get_config()

    if config_file["password"]:
        password_option = "Remove Saved Password"
    else:
        password_option = "Save Password"
    
    options = ["Change Credentials", password_option, "Set Editor"]
    option = ""

    while option != components.FilteredList.GO_BACKWARD:
        window.set_header(f"Config | {config_file['email']}")
        option = window.filtered_list(options, "Option")

        if option == "Change Credentials":
            email, password = config.user.create_account(window, scraper)
            save_password = window.create_bool_popup("Save Password", ["Would you like to save your password?"])

            config_file["email"] = email

            if save_password:
                config.user.encode_password(config_file, password)

            config.user.write_config(config_file)

        elif option == "Save Password":
            # First, get password and verify it is correct
            email = config_file["email"]
            while True:
                password = config.user.get_password(window)

                if config.user.authenticate(window, scraper, email, password):
                    config.user.encode_password(config_file, password)
                    config.user.write_config(config_file)
                    break
            
            window.create_popup("Saved Password", ["Password successfully saved"])

        elif option == "Remove Saved Password":
            config_file["password"] = ""
            config.user.write_config(config_file)

            window.create_popup("Removed Password", ["Password successfully removed"])

        elif option == "Set Editor":
            editor = window.filtered_list(list(config.user.EDITORS.keys()), "Editor")

            if editor == 0:
                break

            config_file["editor"] = editor
            config.user.write_config(config_file)

def other_menu():
    window = Window.get_window()
    students = get_students()
    labs = get_labs()

    window.set_header(f"String Match")
    scraper = Zyscrape()

    # Choose lab
    assignment = window.filtered_list(labs, "Assignment", Lab.find)
    if assignment is 0:
        return

    # Select the lab part if needed
    if len(assignment.parts) > 1:
        p = window.filtered_list([name for name in assignment.parts], "Part")
        if p is 0:
            return
        part = assignment.parts[assignment.parts.index(p)]
    else:
        part = assignment.parts[0]

    search_string = window.text_input("Enter a search string")

    output_path = window.text_input("Enter the output path including filename [~ is supported]")

    logger = window.new_logger()

    log_file = open(os.path.expanduser(output_path), "w")
    student_num = 1

    for student in students:
        logger.log(f"[{student_num}/{len(students)}] Checking {student.full_name}")

        match_result = scraper.check_submissions(str(student.id), part, search_string)

        if match_result["success"]:
            log_file.write(f"{student.full_name} matched {match_result['time']}\n")

            logger.append(f" found {search_string}")

        # Check for and log errors
        if "error" in match_result:
            log_file.write(f"ERROR on {student.full_name}: {match_result['error']}")

        student_num += 1

    window.remove_logger(logger)
    log_file.close()

def mainloop_callback(option):
    if option == "Grade":
        grader.grade()
    elif option == "Config":
        config_menu()
    elif option == "String Match":
        other_menu()

""" Main program loop """
def mainloop(admin_mode):
    window = Window.get_window()
    config_file = config.user.get_config()
    
    if admin_mode:
        options = ["Grade", "Config", "String Match"]
    else:
        options = ["Grade", "Config"]

    window.set_header(f"Menu | {config_file['email']}")
    window.filtered_list(options, "Option", mainloop_callback)

""" zygrade startpoint """
def main(window: Window):
    # Read args to set admin mode
    if "-a" in sys.argv:
        admin = True
    else:
        admin = False
    
    # Ensure config directories exist
    config.zygrader.start()

    # Log in user
    config.user.initial_config(window)

    # Apply versioning
    config.versioning.do_versioning(window)

    # Load student and lab data on startup
    get_students()
    get_labs()

    mainloop(admin)

def start():
    # Create a zygrader window
    Window(main, "zygrader")
