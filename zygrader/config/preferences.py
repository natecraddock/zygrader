"""Preferences: Functions for managing user preferences"""
import os
import json
import base64

from .shared import SharedData

EDITORS = {
    "Pluma": "/usr/bin/pluma",
    "Gedit": "/usr/bin/gedit",
    "VSCode": "/usr/bin/code",
    "Atom": "/usr/bin/atom",
    "Vim": "/usr/bin/vim",
    "Emacs": "/usr/bin/emacs",
    "Nano": "/bin/nano",
    "Less": "/usr/bin/less"
}

DEFAULT_CONFIG = {
    "version": SharedData.VERSION.vstring,
    "email": "",
    "password": "",
    "clear_filter": "",
    "left_right_arrow_nav": "left_right_arrow_nav",
    "editor": "Pluma",
    "data_dir": "",
    "class_code": "No Override",
    "dark_mode": "",
}

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".config/zygrader")
CONFIG_FILE = "config.json"

def install(config_dir):
    """Create the user's configuration directory"""
    # Create config directory
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)

    # Create config file
    if not os.path.exists(os.path.join(config_dir, CONFIG_FILE)):
        with open(os.path.join(config_dir, CONFIG_FILE), "w") as config_file:
            json.dump(DEFAULT_CONFIG, config_file)

def initial_config():
    """Wrapper around install() to set the path for the config directory"""
    # Ensure user config exists
    install(CONFIG_PATH)

def write_config(config):
    """Write the user's config to disk"""
    config_path = os.path.join(CONFIG_PATH, CONFIG_FILE)

    with open(config_path, "w") as config_file:
        json.dump(config, config_file)

def get_config():
    """Get the user's config from disk"""
    config_path = os.path.join(CONFIG_PATH, CONFIG_FILE)

    with open(config_path, "r") as config_file:
        return json.load(config_file)

def is_preference_set(pref):
    """Return True if a preference is set, False otherwise"""
    return pref in get_config()

def get_preference(pref):
    """Get a preference from the config file"""
    config = get_config()
    if pref in config:
        return config[pref]
    return ""

def decode_password(config):
    """Decode a base64 encoded password"""
    decoded = base64.b64decode(config["password"])
    return decoded.decode("utf-8")

def encode_password(config, password):
    """Encode a password in base64 for slight security"""
    encode = base64.b64encode(password.encode("ascii"))
    config["password"] = str(encode, "utf-8")

def set_data_directory(path):
    """Set the 'data_dir' preference to 'path'"""
    if not os.path.exists(path):
        return False

    config = get_config()
    config["data_dir"] = path
    write_config(config)
    return True
