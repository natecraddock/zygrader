import os

from zygrader.ui.window import Window
from zygrader.ui import components
from . import preferences
from .shared import SharedData

def load_changelog():
    """Load the changelog into an array of lines"""
    lines = []
    changelog = os.path.join(os.path.dirname(__file__), "changelog.txt")
    with open(changelog, "r") as _file:
        for line in _file:
            # Ignore comments in the changelog
            if not line.startswith("#"):
                lines.append(line.rstrip())
    return lines

def get_version_message(version):
    """Get the message for the zygrader version from the changelog"""
    changelog = load_changelog()

    msg = [f"zygrader version {version}", ""]

    version_index = 0
    for line in changelog:
        if line == str(version):
            version_index = changelog.index(line) + 1

    line = changelog[version_index]
    while line:
        msg.append(line)
        version_index += 1
        line = changelog[version_index]

    return msg

def compare_versions(zygrader_version, user_version):
    return user_version < zygrader_version

def write_current_version(config):
    config["version"] = SharedData.VERSION
    preferences.write_config(config)

def do_versioning(window: Window):
    """Compare the user's current version in the config and make necessary adjustments
    Also notify the user of new changes"""

    config = preferences.get_config()
    user_version = config["version"]

    # Special case to convert strings in v1.0 config files to floats for future compatibility
    if user_version == "1.0":
        config["version"] = 1.0
        preferences.write_config(config)
        user_version = 1.0

    if compare_versions(1.1, user_version):
        msg = get_version_message(1.1)

        window.create_popup("Version 1.1", msg, components.Popup.ALIGN_LEFT)
    
    if compare_versions(1.2, user_version):
        msg = get_version_message(1.2)

        window.create_popup("Version 1.2", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.3, user_version):
        # Add Pluma as the default editor to the user config
        config["editor"] = "Pluma"
        preferences.write_config(config)

        msg = get_version_message(1.3)

        window.create_popup("Version 1.3", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.4, user_version):
        msg =  get_version_message(1.4)

        window.create_popup("Version 1.4", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.5, user_version):
        msg =  get_version_message(1.5)

        window.create_popup("Version 1.5", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.6, user_version):
        msg =  get_version_message(1.6)

        window.create_popup("Version 1.6", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.7, user_version):
        msg =  get_version_message(1.7)

        window.create_popup("Version 1.7", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(1.8, user_version):
        msg = get_version_message(1.8)

        window.create_popup("Version 1.8", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.0, user_version):
        msg = get_version_message(2.0)

        window.create_popup("Version 2.0", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.1, user_version):
        msg = get_version_message(2.1)

        window.create_popup("Version 2.1", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.2, user_version):
        msg = get_version_message(2.2)

        window.create_popup("Version 2.2", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.3, user_version):
        msg = get_version_message(2.3)

        window.create_popup("Version 2.3", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.4, user_version):
        msg = get_version_message(2.4)

        window.create_popup("Version 2.4", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.5, user_version):
        msg = get_version_message(2.5)

        window.create_popup("Version 2.5", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.51, user_version):
        msg = get_version_message(2.51)

        window.create_popup("Version 2.51", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.6, user_version):
        msg = get_version_message(2.6)

        window.create_popup("Version 2.6", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.7, user_version):
        msg = get_version_message(2.7)

        window.create_popup("Version 2.7", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.8, user_version):
        msg = get_version_message(2.8)

        window.create_popup("Version 2.8", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.81, user_version):
        msg = get_version_message(2.81)

        window.create_popup("Version 2.81", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.82, user_version):
        # Add left right arrow navigation on the menu to default config
        config["left_right_arrow_nav"] = ""
        preferences.write_config(config)
        window.update_preferences()

    if compare_versions(2.9, user_version):
        msg = get_version_message(2.9)

        window.create_popup("Version 2.9", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(2.91, user_version):
        # Configure users to use the browser diffing by default
        config["browser_diff"] = ""
        preferences.write_config(config)

    if compare_versions(3.0, user_version):
        msg = get_version_message(3.0)

        window.create_popup("Version 3.0", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(3.1, user_version):
        msg = get_version_message(3.1)

        window.create_popup("Version 3.1", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(3.14, user_version):
        msg = get_version_message(3.14)
        config["clear_filter"] = ""
        preferences.write_config(config)

        window.create_popup("Version π (3.14)", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(3.2, user_version):
        msg = get_version_message(3.2)

        window.create_popup("Version 3.2", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(3.3, user_version):
        msg = get_version_message(3.3)

        window.create_popup("Version 3.3", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(3.4, user_version):
        msg = get_version_message(3.4)

        window.create_popup("Version 3.4", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(3.5, user_version):
        msg = get_version_message(3.5)

        window.create_popup("Version 3.5", msg, components.Popup.ALIGN_LEFT)

    if compare_versions(3.5, user_version):
        msg = get_version_message(3.6)

        window.create_popup("Version 3.6", msg, components.Popup.ALIGN_LEFT)

    # Write the current version to the user's config file
    write_current_version(config)
