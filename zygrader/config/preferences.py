"""Preferences: Functions for managing user preferences"""
import json
import os
import typing

from .shared import SharedData

# Valid text editors for viewing submissions.
EDITORS = {
    "Pluma": "/usr/bin/pluma",
    "Gedit": "/usr/bin/gedit",
    "VSCode": "/usr/bin/code",
    "Atom": "/usr/bin/atom",
    "Vim": "/usr/bin/vim",
    "Emacs": "/usr/bin/emacs",
    "Nano": "/bin/nano",
    "Less": "/usr/bin/less",
}

# The default configuration for a new user of zygrader.
# Also used for determining if a key is valid for set() and get().
DEFAULT_PREFERENCES = {
    "version": SharedData.VERSION.vstring,
    "email": "",
    "password": "",
    "left_right_arrow_nav": True,
    "use_esc_back": False,
    "clear_filter": True,
    "vim_mode": False,
    "dark_mode": True,
    "christmas_mode": False,
    "spooky_mode": False,
    "browser_diff": False,
    "save_password": False,
    "class_code": "No Override",
    "editor": "Pluma",
    "data_dir": "",
    "output_dir": "~",
}

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".config/zygrader")
CONFIG_FILE = "config.json"

# Store the current user preferences in memory to prevent frequent disk access.
PREFERENCES = {}

# Callback functions for entities interested in knowing when preferences are updated.
OBSERVERS = []


def update_observers():
    for observer_fn in OBSERVERS:
        observer_fn()


def write_config(config):
    """Write the user's config to disk"""
    config_path = os.path.join(CONFIG_PATH, CONFIG_FILE)

    with open(config_path, "w") as config_file:
        json.dump(config, config_file)


def get_config() -> dict:
    """Get the user's config from disk"""
    global PREFERENCES
    config_path = os.path.join(CONFIG_PATH, CONFIG_FILE)

    with open(config_path, "r") as config_file:
        PREFERENCES = json.load(config_file)

    return PREFERENCES


def get(key: str) -> typing.Union[str, bool]:
    """Get a preference"""
    if key not in DEFAULT_PREFERENCES:
        raise KeyError("Invalid Preferences Key")

    if PREFERENCES == {}:
        get_config()

    return PREFERENCES[key]


def set(key: str, value: typing.Union[str, bool]):
    """Set a preference"""
    if key not in DEFAULT_PREFERENCES:
        raise KeyError("Invalid Preferences Key")

    PREFERENCES[key] = value

    # Write preferences every time they are set
    write_config(PREFERENCES)

    # Notify observers
    update_observers()


def add_observer(observer_fn):
    """Register a function to be called when the preferences are saved"""
    OBSERVERS.append(observer_fn)


def install(config_dir):
    """Create the user's configuration directory"""
    # Create config directory
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # Create config file
    if not os.path.exists(os.path.join(config_dir, CONFIG_FILE)):
        with open(os.path.join(config_dir, CONFIG_FILE), "w") as config_file:
            json.dump(DEFAULT_PREFERENCES, config_file)


def initialize():
    """Wrapper around install() to set the path for the config directory"""
    # Ensure user config exists
    install(CONFIG_PATH)

    # Load preferences into memory
    get_config()


def set_data_directory(path):
    """Set the 'data_dir' preference to 'path'"""
    if not os.path.exists(path):
        return False

    set("data_dir", path)
    return True
