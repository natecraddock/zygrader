import os

from distutils.version import LooseVersion

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

def get_version_message(version: str):
    """Get the message for the zygrader version from the changelog"""
    changelog = load_changelog()

    msg = [f"zygrader version {version}", ""]

    version_index = 0
    for line in changelog:
        if line == version:
            version_index = changelog.index(line) + 1

    line = changelog[version_index]
    while line:
        msg.append(line)
        version_index += 1
        line = changelog[version_index]

    return msg

def compare_versions(zygrader_version, user_version):
    return LooseVersion(user_version) < LooseVersion(zygrader_version)

def write_current_version(config):
    config["version"] = SharedData.VERSION.vstring
    preferences.write_config(config)

def do_versioning(window: Window):
    """Compare the user's current version in the config and make necessary adjustments
    Also notify the user of new changes"""

    config = preferences.get_config()
    user_version = config["version"]

    if isinstance(user_version, float):
        user_version = str(user_version)

    version = "4.0.0"
    if compare_versions(version, user_version):
        msg = get_version_message(version)

        window.create_popup(f"Version {version}", msg, components.Popup.ALIGN_LEFT)

    version = "4.1.0"
    if compare_versions(version, user_version):
        msg = get_version_message(version)

        # Add new default preference
        config["class_code"] = "No Override"

        window.create_popup(f"Version {version}", msg, components.Popup.ALIGN_LEFT)

    version = "4.2.0"
    if compare_versions(version, user_version):
        msg = get_version_message(version)

        window.create_popup(f"Version {version}", msg, components.Popup.ALIGN_LEFT)

    version = "4.7.1"
    if compare_versions(version, user_version):
        msg = get_version_message(version)

        window.create_popup(f"Version {version}", msg, components.Popup.ALIGN_LEFT)

    # Write the current version to the user's config file
    write_current_version(config)
