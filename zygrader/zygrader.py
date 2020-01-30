import os
import sys

from . import data
from . import config
from . import grader
from . import admin

from .zybooks import Zybooks

from .ui import window
from .ui.window import Window
from .ui import components

def config_menu():
    window = Window.get_window()
    zy_api = Zybooks()
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
            email, password = config.user.create_account(window, zy_api)
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

                if config.user.authenticate(window, zy_api, email, password):
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

def prep_lab_score_calc():
    window = Window.get_window()

    try:
        score = float(window.text_input("What was the student's original score"))
        new_score = score + ((100 - score) * 0.6)

        window.create_popup("New Score", [f"The student's new score is: {new_score}"])
    except ValueError:
        window.create_popup("Error", ["Invalid input"])

def mainloop_callback(option):
    if option == "Grade":
        grader.grade()
    elif option == "Config":
        config_menu()
    elif option == "Prep Lab Score Calculator":
        prep_lab_score_calc()
    elif option == "Admin":
        admin.admin_menu()

""" Main program loop """
def mainloop(admin_mode):
    window = Window.get_window()
    config_file = config.user.get_config()
    
    options = ["Grade", "Config", "Prep Lab Score Calculator"]

    if admin_mode:
        options.append("Admin")

    window.set_header(f"Menu | {config_file['email']}")
    window.filtered_list(options, "Option", mainloop_callback)

""" zygrade startpoint """
def main(window: Window):
    # Read args to set admin mode
    if "-a" in sys.argv:
        admin = True
    else:
        admin = False
    
    # Start application and load data
    config.g_data.start()

    # Log in user
    config.user.initial_config(window)

    # Apply versioning
    config.versioning.do_versioning(window)

    mainloop(admin)

def start():
    # Create a zygrader window
    Window(main, "zygrader")
