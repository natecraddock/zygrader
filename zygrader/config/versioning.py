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
    
    # Write the current version to the user's config file
    write_current_version(config)
