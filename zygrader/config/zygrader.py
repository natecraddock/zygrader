import os
import json

from .. import data

# Only change these if you know what you are doing!
VERSION = 1.8

# TODO: save this in configuration
CLASS_CODE = ""

# The zygrader data exists in a hidden folder in the same directory
# as the zygrader module. This folder contains the global configuration
# and the folders for each semester/class that zygrader has been initialized
# for. This folder is automatically created when zygrader is executed
# if the folder does not exist.
DATA_DIRECTORY = ".zygrader_data"
CLASS_DIRECTORY = ""
GLOBAL_CONFIG_PATH = os.path.join(DATA_DIRECTORY, "config")

STUDENT_DATA = ""
LABS_DATA = ""

def get_global_config():
    config = {}
    with open(GLOBAL_CONFIG_PATH, 'r') as _file:
        config = json.load(_file)

    return config

def write_global_config(config):
    with open(GLOBAL_CONFIG_PATH, 'w') as _file:
        json.dump(config, _file)

def setup_data_directory():
    """If no data directory exists, create it"""
    if not os.path.exists(DATA_DIRECTORY):
        os.mkdir(DATA_DIRECTORY)
    
    # Ensure the config file exists in the directory
    if not os.path.exists(GLOBAL_CONFIG_PATH):
        global_config = {"class_code": "", "class_codes": []}
        write_global_config(global_config)    
    # Ensure the config file exists in the directory
    if not os.path.exists(GLOBAL_CONFIG_PATH):
        global_config = {"class_code": "", "class_codes": []}
        write_global_config(global_config)

def start():
    global CLASS_CODE
    global CLASS_DIRECTORY
    global STUDENT_DATA
    global LABS_DATA

    setup_data_directory()
    global_config = get_global_config()

    # Look for the current class directory
    current_class_code = global_config["class_code"]
    if current_class_code:
        CLASS_CODE = current_class_code
        CLASS_DIRECTORY = os.path.join(DATA_DIRECTORY, current_class_code)

        STUDENT_DATA = os.path.join(CLASS_DIRECTORY, "students.json")
        LABS_DATA = os.path.join(CLASS_DIRECTORY, "labs.json")

        # Load data for the current class
        data.get_students()
        data.get_labs()

def get_class_codes():
    config = get_global_config()
    return config["class_codes"]

def set_class_codes(codes):
    config = get_global_config()
    config["class_codes"] = codes

    write_global_config(config)

def get_current_class_code():
    config = get_global_config()
    return config["class_code"]

def set_current_class_code(code):
    config = get_global_config()
    config["class_code"] = code

    write_global_config(config)