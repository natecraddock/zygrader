import os
import json
import time
import base64

from .. import zybooks
from ..ui.window import Window
from ..ui.components import TextInput

from . import g_data

EDITORS = {
    "Pluma": "/usr/bin/pluma",
    "Gedit": "/usr/bin/gedit",
    "VSCode": "/usr/bin/code",
    "Atom": "/usr/bin/atom",
}

def install(config_dir):
    # Create config directory
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)

    # Create config file
    if not os.path.exists(os.path.join(config_dir, "config")):
        config = {"version": g_data.VERSION, "email": "", "password":""}
        with open(os.path.join(config_dir, "config"), "w") as config_file:
            json.dump(config, config_file)

def write_config(config):
    config_dir = os.path.join(os.path.expanduser("~"), ".zygrader/")
    config_path = os.path.join(config_dir, "config")

    with open(config_path, "w") as config_file:
        json.dump(config, config_file)

def get_config():
    config_dir = os.path.join(os.path.expanduser("~"), ".zygrader/")
    config_path = os.path.join(config_dir, "config")

    with open(config_path, "r") as config_file:
        return json.load(config_file)

def decode_password(config):
    return base64.b64decode(config["password"])

def encode_password(config, password):
    encode = base64.b64encode(password.encode("ascii"))
    config["password"] = str(encode, "utf-8")

def authenticate(window: Window, zy_api, email, password):
    if zy_api.authenticate(email, password):
        window.create_popup("Success", [f"Successfully Authenticated {email}"])
        return True
    else:
        window.create_popup("Error", ["Invalid Credentials"])
        return False

def get_password(window: Window):
    window.set_header("Sign In")

    password = window.text_input("Enter your zyBooks password", mask=TextInput.TEXT_MASKED)

    return password

# Create a user account
def create_account(window: Window, zy_api):
    window.set_header("Sign In")

    while True:
        # Get user account information
        email = window.text_input("Enter your zyBooks email", mask=None)
        password = get_password(window)

        if authenticate(window, zy_api, email, password):
            break
    
    return email, password

def initial_config(window: Window):
    zy_api = zybooks.Zybooks()

    config_dir = os.path.join(os.path.expanduser("~"), ".zygrader/")
    config_path = os.path.join(config_dir, "config")

    # Ensure user config exists
    install(config_dir)

    # Check if user has email/password information
    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    # If user email and password exists, authenticate and return
    if config["email"] and config["password"]:
        password = decode_password(config)
        authenticate(window, zy_api, config["email"], password)
        return config

    # User does not have account created
    if not config["email"]:
        email, password = create_account(window, zy_api)

        save_password = window.create_bool_popup("Save Password", ["Would you like to save your password?"])

        config["email"] = email

        if save_password:
            encode_password(config, password)

        write_config(config)

    # User has not saved password, reprompt
    elif not config["password"]:
        email = config["email"]

        while True:
            password = get_password(window)

            if authenticate(window, zy_api, email, password):
                break

    return config
