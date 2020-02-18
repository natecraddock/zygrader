import os
import sys

from . import data
from . import config
from . import grader
from . import admin
from . import logger

from .zybooks import Zybooks

from .ui import window
from .ui.window import Window
from .ui import components


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
        config.user.config_menu()
    elif option == "Prep Lab Score Calculator":
        logger.log("prep lab score calculator tool accessed")
        prep_lab_score_calc()
    elif option == "Admin":
        logger.log("admin menu accessed")
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

    logger.log("zygrader started")

    mainloop(admin)

def start():
    # Create a zygrader window, callback to main function
    Window(main, "zygrader")
