"""Zygrader: Main menu for zygrader"""
import sys

from . import data
from . import config
from . import grader
from . import admin
from . import logger
from . import utils

from .ui.window import WinContext, Window

MAIN_MENU_OPTIONS = ["Grade", "Prep Lab Score Calculator", "Run For Fun",
                     "View Students", "Preferences", "Changelog"]

def mainloop_callback(context: WinContext):
    """Run the chosen option from the main menu"""
    option = MAIN_MENU_OPTIONS[context.data]

    if option == "Grade":
        grader.grade()
    elif option == "Run For Fun":
        grader.grade(use_locks=False)
    elif option == "Preferences":
        config.user.preferences_menu()
    elif option == "Prep Lab Score Calculator":
        logger.log("prep lab score calculator tool accessed")
        utils.prep_lab_score_calc()
    elif option == "Admin":
        logger.log("admin menu accessed")
        admin.admin_menu()
    elif option == "Changelog":
        lines = config.versioning.load_changelog()
        context.window.create_list_popup("Changelog", lines)
    elif option == "View Students":
        utils.view_students()

def mainloop(admin_mode):
    """Create the main menu that runs until zygrader is exited"""
    window = Window.get_window()

    if admin_mode:
        MAIN_MENU_OPTIONS.append("Admin")

    window.set_header(f"Menu")
    window.create_filtered_list("Option", input_data=MAIN_MENU_OPTIONS, callback=mainloop_callback)

def main(window: Window):
    """Curses has been initialized, now setup various modules before showing the menu"""
    # Read args to set admin mode
    if "-a" in sys.argv:
        admin_mode = True
    else:
        admin_mode = False

    # Apply versioning
    config.versioning.do_versioning(window)

    # Log in user
    config.user.login(window)

    # Start file watch thread
    data.fs_watch.start_fs_watch()

    logger.log("zygrader started")

    mainloop(admin_mode)

def start():
    """Setup the user before initializing curses"""
    # Start application and setup data folders
    config.g_data.start()

    # Setup user configuration
    config.user.initial_config()

    # Create a zygrader window, callback to main function
    Window(main, "zygrader")
