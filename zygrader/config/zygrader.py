import os
import json

# Only change these if you know what you are doing!
VERSION = "1.0"

# TODO: save this in configuration
CLASS_CODE = "BYUCS142Fall2019"

DATA_DIRECTORY = ".zygrader_data"
STUDENT_DATA = os.path.join(DATA_DIRECTORY, "students.json")
LABS_DATA = os.path.join(DATA_DIRECTORY, "labs.json")

def setup_data_directory():
    """If no data directory exists, create it"""
    if not os.path.exists(DATA_DIRECTORY):
        os.mkdir(DATA_DIRECTORY)

    # TODO: ensure that the STUDENT_DATA and LABS_DATA files exist
    # and are populated with the correct information
    
    # # Ensure the config file exists in the directory
    # if not os.path.exists(os.path.join(DATA_DIRECTORY, "config")):
    #     data = {""}

def start():
    setup_data_directory()