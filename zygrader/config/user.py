import os
import json
import time
import base64

from .. import zybooks
from ..ui.window import Window
from ..ui.components import TextInput, FilteredList, Popup

from . import g_data

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
    if password == Window.CANCEL:
        password = ""

    return password

# Create a user account
def create_account(window: Window, zy_api):
    window.set_header("Sign In")

    while True:
        # Get user account information
        email = window.text_input("Enter your zyBooks email", mask=None)
        if email == Window.CANCEL:
            email = ""
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
    if "email" in config and "password" in config and config["password"]:
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
    elif "password" in config and not config["password"]:
        email = config["email"]

        while True:
            password = get_password(window)

            if authenticate(window, zy_api, email, password):
                break

    return config

def toggle_preference(pref):
    config = get_config()

    if pref in config:
        del config[pref]
    else:
        config[pref] = ""

    write_config(config)

def get_preference(pref):
    """Return True if a preference is set, False otherwise"""
    return pref in get_config()

preferences = {"left_right_arrow_nav": "Left/Right Arrow Navigation",
                "vim_mode": "Vim Mode",
                "dark_mode": "Dark Mode",
                "christmas_mode": "Christmas Theme",
                }

def draw_preferences():
    list = []
    for pref, name in preferences.items():
        if get_preference(pref):
            list.append(f"[X] {name}")
        else:
            list.append(f"[ ] {name}")

    return list

def preferences_callback(selected_index):
    window = Window.get_window()

    toggle_preference(list(preferences.keys())[selected_index - 1])
    window.update_preferences()

def config_menu():
    window = Window.get_window()
    zy_api = zybooks.Zybooks()
    config_file = get_config()

    if "password" in config_file:
        password_option = "Remove Saved Password"
    else:
        password_option = "Save Password"
    
    options = ["Change Credentials", password_option, "Set Editor", "Preferences"]
    option = ""

    while option != FilteredList.GO_BACKWARD:
        window.set_header(f"Config | {config_file['email']}")
        option = window.filtered_list(options, "Option")

        if option == "Change Credentials":
            email, password = create_account(window, zy_api)
            save_password = window.create_bool_popup("Save Password", ["Would you like to save your password?"])

            config_file["email"] = email

            if save_password:
                encode_password(config_file, password)
            else:
                pass

            write_config(config_file)

        elif option == "Save Password":
            # First, get password and verify it is correct
            email = config_file["email"]
            while True:
                password = get_password(window)

                if authenticate(window, zy_api, email, password):
                    encode_password(config_file, password)
                    write_config(config_file)
                    break
            
            window.create_popup("Saved Password", ["Password successfully saved"])

        elif option == "Remove Saved Password":
            config_file["password"] = ""
            write_config(config_file)

            window.create_popup("Removed Password", ["Password successfully removed"])

        elif option == "Set Editor":
            editor = window.filtered_list(list(EDITORS.keys()), "Editor")

            if editor == 0:
                break

            config_file["editor"] = editor
            write_config(config_file)

        elif option == "Preferences":
            window.create_list_popup("User Preferences", callback=preferences_callback, list_fill=draw_preferences)
