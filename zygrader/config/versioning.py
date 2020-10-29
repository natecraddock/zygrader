import os
from distutils.version import LooseVersion

from zygrader import ui

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


def update_user_version():
    preferences.set("version", SharedData.VERSION.vstring)


def versioning_update_preferences():
    """Compare the user's current version in the config and make necessary adjustments."""

    # To modify the config with more flexibility, we need access to the raw json.
    config = preferences.get_config()
    user_version = config["version"]

    if isinstance(user_version, float):
        user_version = str(user_version)

    version = "4.1.0"
    if compare_versions(version, user_version):
        # Add new default preference
        config["class_code"] = "No Override"

    version = "4.8.0"
    if compare_versions(version, user_version):
        # Preferences are now stored as true/false json values,
        # rather than relying on the presence of a key. Update existing
        # user's preferences.

        # Update booleans.
        for key in {
                "left_right_arrow_nav", "use_esc_back", "clear_filter",
                "vim_mode", "dark_mode", "christmas_mode", "browser_diff",
                "save_password"
        }:
            if key in config:
                config[key] = True
            else:
                config[key] = False

        # Set string preferences to their defaults if they don't exist.
        if not "version" in config:
            config["verison"] = SharedData.VERSION.vstring
        if not "email" in config:
            config["email"] = ""
        if not "password" in config:
            config["password"] = ""
        if not "class_code" in config:
            config["class_code"] = "No Override"
        if not "editor" in config:
            config["editor"] = "Pluma"
        if not "data_dir" in config:
            config["data_dir"] = ""

    version = "4.9.0"
    if compare_versions(version, user_version):
        config["spooky_mode"] = False

    version = "5.0.0"
    if compare_versions(version, user_version):
        config["unicode_mode"] = False


def find_versioning_message(window, version, user_version):
    """Display a versioning message for the given version number if one exists."""
    if compare_versions(version, user_version):
        popup = ui.layers.Popup(f"Version {version}")
        popup.set_message(get_version_message(version))
        window.run_layer(popup)

        return True
    return False


def show_versioning_message(window: ui.Window):
    """Notify the user of all logged changes since their last update."""

    user_version = preferences.get("version")

    # Add a version string for this array for each version that will show an update popup
    update_versions = ["4.0.0", "4.1.0", "4.2.0", "4.7.1", "4.8.8"]

    updated = False
    for version in update_versions:
        if find_versioning_message(window, version, user_version):
            updated = True

    version = "4.9.0"
    if compare_versions(version, user_version):
        msg = get_version_message(version)
        window.create_popup(f"Version {version}", msg,
                            ui.components.Popup.ALIGN_LEFT)

    # Write the current version to the user's config file.
    # It is important to not update the number in do_versioning,
    # otherwise the version number here will be updated and popups
    # will not show.
    if updated:
        update_user_version()
