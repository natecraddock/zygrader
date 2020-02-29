import os
import json

from .. import data

# Only change these if you know what you are doing!
VERSION = 2.81

# TODO: save this in configuration
CLASS_CODE = ""

# The zygrader data exists in a hidden folder in the same directory
# as the zygrader module. This folder contains the global configuration
# and the folders for each semester/class that zygrader has been initialized
# for. This folder is automatically created when zygrader is executed
# if the folder does not exist.
ZYGRADER_DATA_DIRECTORY = ".zygrader_data"
CLASS_DIRECTORY = ""
LOGS_DIRECTORY = "logs"
DATA_DIRECTORY = ".data"
CACHE_DIRECTORY = ".cache"
LOCKS_DIRECTORY = ".locks"

STUDENTS_FILE = "students.json"
LABS_FILE = "labs.json"

# This is a global to represent if student code is being executed
RUNNING_CODE = False
running_process = None

GLOBAL_CONFIG_PATH = os.path.join(ZYGRADER_DATA_DIRECTORY, "config")

def get_global_config():
    config = {}
    with open(GLOBAL_CONFIG_PATH, 'r') as _file:
        config = json.load(_file)

    return config

def write_global_config(config):
    with open(GLOBAL_CONFIG_PATH, 'w') as _file:
        json.dump(config, _file)

def get_config_directory(config_type):
    """Return path of config directory. Create directory if it does not exist"""
    _path =  os.path.join(CLASS_DIRECTORY, config_type)
    if not os.path.exists(_path):
        os.mkdir(_path)
    return _path

def get_logs_directory():
    return get_config_directory(LOGS_DIRECTORY)

def get_data_directory():
    return get_config_directory(DATA_DIRECTORY)

def get_cache_directory():
    return get_config_directory(CACHE_DIRECTORY)

def get_locks_directory():
    return get_config_directory(LOCKS_DIRECTORY)

def get_student_data():
    return os.path.join(get_data_directory(), STUDENTS_FILE)

def get_labs_data():
    return os.path.join(get_data_directory(), LABS_FILE)

def setup_zygrader_data_directory():
    """If no data directory exists, create it"""
    if not os.path.exists(ZYGRADER_DATA_DIRECTORY):
        os.mkdir(ZYGRADER_DATA_DIRECTORY)
    
    # Ensure the config file exists in the directory
    if not os.path.exists(GLOBAL_CONFIG_PATH):
        global_config = {"class_code": "", "class_codes": []}
        write_global_config(global_config)

def setup_class_directory(code):
    global CLASS_CODE
    global CLASS_DIRECTORY

    CLASS_CODE = code
    CLASS_DIRECTORY = os.path.join(ZYGRADER_DATA_DIRECTORY, code)

    if not os.path.exists(CLASS_DIRECTORY):
        os.mkdir(CLASS_DIRECTORY)

    # Load data for the current class
    data.get_students()
    data.get_labs()

def start():
    setup_zygrader_data_directory()
    global_config = get_global_config()

    # Look for the current class directory
    current_class_code = global_config["class_code"]
    if current_class_code:
        setup_class_directory(current_class_code)

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

    # If the code is not in the list, add it
    if code not in config["class_codes"]:
        config["class_codes"].append(code)

    setup_class_directory(code)
    write_global_config(config)

def add_class(code):
    config = get_global_config()

    # Don't allow duplicates
    if code in config["class_codes"]:
        return

    set_current_class_code(code)
