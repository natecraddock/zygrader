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
    window.set_header("Prep Lab Calculator")

    try:
        score = float(window.create_text_input("What was the student's original score"))
        if score == Window.CANCEL:
            return

        new_score = score + ((100 - score) * 0.6)
        window.create_popup("New Score", [f"The student's new score is: {new_score}"])
    except ValueError:
        window.create_popup("Error", ["Invalid input"])

def view_students_callback(student_index):
    window = Window.get_window()
    students = data.get_students()

    student = students[student_index]

    msg = [f"Name: {student.full_name}", f"Email: {student.email}", f"Section: {student.section}", f"ID: {student.id}"]
    window.create_popup("Student Info", msg, components.Popup.ALIGN_LEFT)


def view_students():
    window = Window.get_window()
    students = data.get_students()
    window.set_header("View Students")

    window.create_filtered_list(students, "Student Name", callback=view_students_callback)

main_menu_options = ["Grade", "Prep Lab Score Calculator", "Run For Fun", "View Students", "Preferences", "Changelog"]

def mainloop_callback(option_index):
    option = main_menu_options[option_index]

    if option == "Grade":
        grader.grade()
    elif option == "Run For Fun":
        grader.grade(use_locks=False)
    elif option == "Preferences":
        config.user.preferences_menu()
    elif option == "Prep Lab Score Calculator":
        logger.log("prep lab score calculator tool accessed")
        prep_lab_score_calc()
    elif option == "Admin":
        logger.log("admin menu accessed")
        admin.admin_menu()
    elif option == "Changelog":
        lines = config.versioning.load_changelog()
        Window.get_window().create_list_popup("Changelog", lines)
    elif option == "View Students":
        view_students()

def mainloop(admin_mode):
    window = Window.get_window()

    if admin_mode:
        main_menu_options.append("Admin")

    window.set_header(f"Menu")
    window.create_filtered_list(main_menu_options, "Option", mainloop_callback)

def main(window: Window):
    # Read args to set admin mode
    if "-a" in sys.argv:
        admin = True
    else:
        admin = False

    # Apply versioning
    config.versioning.do_versioning(window)

    # Log in user
    config.user.login(window)

    logger.log("zygrader started")

    mainloop(admin)

def start():
    # Start application and setup data folders
    config.g_data.start()

    # Setup user configuration
    config.user.initial_config(window)

    # Create a zygrader window, callback to main function
    Window(main, "zygrader")
