import os
from shutil import copyfile

from ..ui.window import Window
from . import user
from . import zygrader

def compare_versions(zygrader_version, user_version):
    return user_version < zygrader_version

def write_current_version(config):
    config["version"] = zygrader.VERSION
    user.write_config(config)

def do_versioning(window: Window):
    """Compare the user's current version in the config and make necessary adjustments
    Also notify the user of new changes"""

    config = user.get_config()
    user_version = config["version"]

    # Special case to convert strings in v1.0 config files to floats for future compatibility
    if user_version == "1.0":
        config["version"] = 1.0
        user.write_config(config)
        user_version = 1.0

    if compare_versions(1.1, user_version):
        msg = ["zygrader Version 1.1", "", "Labels were added to the text search filter boxes",
        "to prompt for a filter string."]

        window.create_popup("Version 1.1", msg)
    
    if compare_versions(1.2, user_version):
        # "Reinstall" zygrader so the admin flag works
        run_path = "/users/groups/cs142ta/tools/zygrader/run"
        copyfile(run_path, os.path.join(os.path.expanduser("~"), "Desktop/zygrader"))
        copyfile(run_path, os.path.join(os.path.expanduser("~"), ".zygrader/zygrader"))

        msg = ["zygrader Version 1.2", "",
               "Show a message when grading a student who has not submitted.",
               "Show netid of the grading TA when a student's submission is locked.",
               "Show a warning if the student's code failed to compile."]

        window.create_popup("Version 1.2", msg)

    if compare_versions(1.3, user_version):
        # Add Pluma as the default editor to the user config
        config["editor"] = "Pluma"
        user.write_config(config)

        msg = ["zygrader Version 1.3", "",
               "Download highest-scoring submissions for exams.",
               "Adds a setting to choose a text editor to open submissions with.",
               "Scrolling past the end of lists will loop back to the beginning.",
               "Lists now highlight the selected entry.",
               "Resizing the terminal is more reliable.",
               "Scrolling through a list quickly has less flickering."]

        window.create_popup("Version 1.3", msg)

    # Write the current version to the user's config file
    write_current_version(config)
