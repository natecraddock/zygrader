import os
from shutil import copyfile

from ..ui.window import Window
from ..ui import components
from . import user
from . import g_data

def compare_versions(zygrader_version, user_version):
    return user_version < zygrader_version

def write_current_version(config):
    config["version"] = g_data.VERSION
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

    if compare_versions(1.4, user_version):
        msg =  ["zygrader Version 1.4", "",
               "* Add Gedit as text editor.",
               "* Left align submission results.",
               "* Replace [l]etter menus with lists. Use the arrow keys to navigate",
               "  all menus in zygrader. Left arrow to go back. Enter or right arrow",
               "  to select an entry.",
               "* Fix: Show all parts of a midterm even if a part was not submitted.",
               "* Fix: Configuration was being reset after versioning.",
               "* Fix: Various submission downloading issues."]

        window.create_popup("Version 1.4", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.5, user_version):
        msg =  ["zygrader Version 1.5", "",
               "* Grader: Show students who are already being graded in red.",
               "* Fix: Various zyBooks download issues.",
               "* Add ability to not count late submissions.",
               "* Cleanup output formatting.",
               "* Refactor windowing system. Now windows are drawn on a stack.",
               "  This means that lists remember which lab/student you chose."]

        window.create_popup("Version 1.5", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.6, user_version):
        msg =  ["zygrader Version 1.6", "",
               "* Fix: Selecting \"Back\" in a list crashed.",
               "* Add ability to grade pair programming.",
               "  After selecting a student, an option is presented to",
               "  select a second student for grading pair programming.",
               "  This will allow you to select a second student, and it zygrader",
               "  will diff the files and open a comparison."]

        window.create_popup("Version 1.6", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.7, user_version):
        msg =  ["zygrader Version 1.7", "",
               "                                    /\\",
               "                               __   \\/   __",
               "* Clear filter after grading   \\_\\_\\/\\/_/_/",
               "* Reduce flashing                _\\_\\/_/_",
               "* Merry Christmas!!!            __/_/\\_\\__",
               "                               /_/ /\\/\\ \\_\\",
               "                                    /\\",
               "                                    \\/",]

        window.create_popup("Version 1.7", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.8, user_version):
        msg = ["zygrader Version 1.8", "",
               "* Stop showing diffs and files immediately.",
               "* Add option to show submitted files.",
               "* Add option to show diff when grading pair programming.",
               "* Fix pair programming sometimes leaving students locked.",
               "* Add lock file remover (run with -a)."]

        window.create_popup("Version 1.8", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.0, user_version):
        msg = ["zygrader Version 2.0", "",
               "* Removed Christmas Theme",
               "* Adds options to setup new zybooks classes",
               "* Adds option to update student roster"]

        window.create_popup("Version 2.0", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.1, user_version):
        msg = ["zygrader Version 2.1", "",
               "* Silence stdout, stderr for external processes.",
               "* Add option to compile and run student code.",
               "  Select a student and then choose \"Run Code\".",
               "* Add a Prep Lab score calculator (for late Prep Labs)"]

        window.create_popup("Version 2.1", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.2, user_version):
        msg = ["zygrader Version 2.2", "",
               "* Add option to diff submission parts.",
               "* Small cleanups."]

        window.create_popup("Version 2.2", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.3, user_version):
        msg = ["zygrader Version 2.3", "",
               "* Allow floating point input for prep lab score calc.",
               "*   (also allows scientific notation too!)",
               "* Use names rather than IDs in lock files.",
               "* Logging of basic data.",
               "* Restructure data directory.",
               "* Docstrings throughout the code.",
               "* Cleanups throughout the code."]

        window.create_popup("Version 2.3", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.4, user_version):
        msg = ["zygrader Version 2.4", "",
               "* More text editors/viewers! (Vim, Emacs, Nano, Less).",
               "    These all open inside the terminal, which means",
               "    grading is now possible over ssh!",
               "    Go to Config > Set Editor to change.",
               "* Run student code in same terminal window.",
               "    Instead of opening in xterm.",
               "* Caching of submission files.",
               "* Fixed a few issues with lock files.",
               "    You can open submissions that you locked."]

        window.create_popup("Version 2.4", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.5, user_version):
        msg = ["zygrader Version 2.5", "",
               "* Allow stopping and pausing student code.",
               "  Press CTRL+C to stop and CTRL+Z to pause.",
               "* Fix pressing \"done\" in pair programming menu.",
               "* Clear the terminal when running student code."]

        window.create_popup("Version 2.5", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.51, user_version):
        msg = ["zygrader Version 2.51", "",
               "* Small fixes.",
               "* Handle SIGHUP to remove locks.",
               "* Add IDs to lock file names to ensure unique locks."]

        window.create_popup("Version 2.51", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.6, user_version):
        msg = ["zygrader Version 2.6", "",
               "* Handle all window resizing crashes.",
               "* Code quality and cleanup.",
               "* Refactor Boolean (yes/no) popup windows."]

        window.create_popup("Version 2.6", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.7, user_version):
        msg = ["zygrader Version 2.7", "",
               "* Add 'Run For Fun' option.",
               "  This allows for running students' code",
               "  without locking submissions."]

        window.create_popup("Version 2.7", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.8, user_version):
        msg = ["zygrader Version 2.8", "",
               "* Add user preferences. Now you can use Vim-style",
               "  keybindings or toggle a very dark mode. :)",
               "  Config > Preferences"]

        window.create_popup("Version 2.8", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.81, user_version):
        msg = ["zygrader Version 2.81", "",
               "* Fix Vim mode.",
               "* Add Christmas Theme to Config > Preferences."
               "* Small optimizations."]

        window.create_popup("Version 2.81", msg, components.Popup.ALIGN_LEFT)

    # Write the current version to the user's config file
    write_current_version(config)
