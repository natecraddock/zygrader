"""Zygrader: Main menu for zygrader"""
import argparse
import getpass
import os
import signal
import sys

from zygrader import admin
from zygrader import config
from zygrader import data
from zygrader import grader
from zygrader import logger
from zygrader import updater
from zygrader import user
from zygrader import utils

from zygrader.config import preferences
from zygrader.config import versioning
from zygrader.config.shared import SharedData
from zygrader.ui.window import WinContext, Window

def lock_cleanup():
    data.lock.unlock_all_labs_by_grader(getpass.getuser())

def sighup_handler(signum, frame):
    lock_cleanup()

def sigint_handler(signum, frame):
    if SharedData.RUNNING_CODE:
        # If child process is running
        if SharedData.running_process.poll() is None:
            SharedData.RUNNING_CODE = False
            SharedData.running_process.send_signal(signal.SIGINT)
            SharedData.running_process = None
    else:
        # Terminating the program
        lock_cleanup()
        sys.exit(0)

def sigtstp_handler(signum, frame):
    if SharedData.RUNNING_CODE:
        # If child process is running
        if SharedData.running_process.poll() is None:
            SharedData.RUNNING_CODE = False
            SharedData.running_process.send_signal(signal.SIGTSTP)

def parse_args():
    """Parse CMD args"""
    parser = argparse.ArgumentParser(description="download and inspect zyBooks data for grading")
    parser.add_argument("-s", "--set-data-dir", help="Data path for shared zygrader files")
    parser.add_argument("--init-data-dir", help="Create the folder for shared zygrader files")
    parser.add_argument("-a", "--admin", action="store_true", help="Enable admin features")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-n", "--no-update", action="store_true", help="Do not check for updates")
    group.add_argument("-i", "--install-version", help="Specify version to install")

    return parser.parse_args()

def handle_args(args):
    if args.set_data_dir:
        if not preferences.set_data_directory(args.set_data_dir):
            print(f"Successfully set the shared data dir to {args.set_data_dir}")
        else:
            print(f"Error: The path \"{args.set_data_dir}\" does not exist.")
            sys.exit()

    if args.init_data_dir:
        if not os.path.exists(args.init_data_dir):
            print(f"Error: the path {args.init_data_dir} does not exist.")
            sys.exit()

        shared_data_dir = os.path.join(args.init_data_dir, '.zygrader_data')

        print(f"Warning: You are about to create the following directory:")
        print(f"{shared_data_dir}")
        print(f"Any existing data will be overwritten.")
        print(f"Type 'Y' to confirm, anything else to cancel: ", end="")

        confirm = input()
        if confirm not in {"Y", "y", "yes", "Yes"}:
            print("Canceled")
            sys.exit()

        SharedData.create_shared_data_directory(shared_data_dir)
        preferences.set_data_directory(shared_data_dir)

        print(f"Successfully created the shared data dir at {shared_data_dir}")
        print()
        print(f"Instruct users to run zygrader with the following flag:")
        print(f"zygrader --set-data-dir {shared_data_dir}")
        sys.exit()

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
        user.preferences_menu()
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
    versioning.do_versioning(window)

    # Log in user
    user.login(window)

    # Start file watch thread
    data.fs_watch.start_fs_watch()

    logger.log("zygrader started")

    mainloop(admin_mode)

def start():
    """Setup before initializing curses"""

    # Handle Signals
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTSTP, sigtstp_handler)
    signal.signal(signal.SIGHUP, sighup_handler)

    # Set a short ESC key delay (curses environment variable)
    os.environ.setdefault('ESCDELAY', '25')

    args = parse_args()

    # Check for updates
    if not args.no_update and not args.install_version:
        latest_version = updater.get_latest_version()
        if latest_version != SharedData.VERSION:
            updater.update_zygrader(latest_version)
            sys.exit()

    if args.install_version:
        updater.install_version(args.install_version)
        sys.exit()

    # Setup user configuration
    preferences.initial_config()

    # Handle configuration based args after config has been initialized
    handle_args(args)

    # Check for shared data dir
    data_dir = preferences.get_preference("data_dir")
    if not data_dir:
        print("You have not set the shared data directory")
        print("Please run with the flag --set-data-dir [path]")
        sys.exit()

    # Start application and setup data folders
    if not SharedData.initialize_shared_data(data_dir):
        sys.exit()

    # Load data for the current class
    data.get_students()
    data.get_labs()

    # Create a zygrader window, callback to main function
    Window(main, f"zygrader {SharedData.VERSION}")

    logger.log("zygrader exited normally")

if __name__ == "__main__":
    start()
