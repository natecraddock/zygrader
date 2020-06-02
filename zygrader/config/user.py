import os
import json
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
    "Vim": "/usr/bin/vim",
    "Emacs": "/usr/bin/emacs",
    "Nano": "/bin/nano",
    "Less": "/usr/bin/less"
}

DEFAULT_CONFIG = {
    "version": g_data.VERSION,
    "email": "",
    "password": "",
    "clear_filter": "",
    "left_right_arrow_nav":"left_right_arrow_nav",
    "editor": "Pluma",
}

def install(config_dir):
    # Create config directory
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)

    # Create config file
    if not os.path.exists(os.path.join(config_dir, "config")):
        config = DEFAULT_CONFIG
        with open(os.path.join(config_dir, "config"), "w") as config_file:
            json.dump(config, config_file)

def initial_config():
    config_dir = os.path.join(os.path.expanduser("~"), ".zygrader/")

    # Ensure user config exists
    install(config_dir)

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

def is_preference_set(pref):
    """Return True if a preference is set, False otherwise"""
    return pref in get_config()

def get_preference(pref):
    config = get_config()
    if pref in config:
        return config[pref]
    return ""

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

def get_email():
    config = get_config()
    if "email" in config:
        return config["email"]
    return ""

def get_password(window: Window):
    window.set_header("Sign In")

    password = window.create_text_input("Enter your zyBooks password", mask=TextInput.TEXT_MASKED)
    if password == Window.CANCEL:
        password = ""

    return password

# Create a user account
def create_account(window: Window, zy_api):
    window.set_header("Sign In")

    while True:
        # Get user account information
        email = window.create_text_input("Enter your zyBooks email", mask=None)
        if email == Window.CANCEL:
            email = ""
        password = get_password(window)

        if authenticate(window, zy_api, email, password):
            break

    return email, password

def login(window: Window):
    zy_api = zybooks.Zybooks()
    config = get_config()

    # If user email and password exists, authenticate and return
    if "email" in config and "password" in config and config["password"]:
        password = decode_password(config)
        authenticate(window, zy_api, config["email"], password)
        window.set_email(config["email"])
        return config

    # User does not have account created
    if not config["email"]:
        email, password = create_account(window, zy_api)

        save_password = window.create_bool_popup("Save Password", ["Would you like to save your password?"])

        config["email"] = email

        if save_password:
            config["save_password"] = ""
            encode_password(config, password)

        write_config(config)
        window.set_email(email)

    # User has not saved password, reprompt
    elif "password" in config and not config["password"]:
        email = config["email"]

        while True:
            password = get_password(window)

            if authenticate(window, zy_api, email, password):
                if is_preference_set("save_password"):
                    encode_password(config, password)
                    write_config(config)
                break

def draw_text_editors():
    options = []
    current_editor = get_preference("editor")

    for name in EDITORS.keys():
        if current_editor == name:
            options.append(f"[X] {name}")
        else:
            options.append(f"[ ] {name}")

    return options

def set_editor(editor_index, pref_name):
    config_file = get_config()
    config_file[pref_name] = list(EDITORS.keys())[editor_index]

    write_config(config_file)

def set_editor_menu(name):
    window = Window.get_window()
    edit_fn = lambda index: set_editor(index, name)
    window.create_list_popup("Set Editor", callback=edit_fn, list_fill=draw_text_editors)

def toggle_preference(pref):
    config = get_config()

    if pref in config:
        del config[pref]
    else:
        config[pref] = ""

    write_config(config)

def password_toggle(name):
    toggle_preference(name)
    config = get_config()

    if name not in config:
        config["password"] = ""
        write_config(config)

    else:
        window = Window.get_window()
        window.create_popup("Remember Password", ["Next time you start zygrader your password will be saved."])

class Preference:
    """Holds information for a user preference item"""
    def __init__(self, name, description, select_fn, toggle=True):
        self.name = name
        self.description = description
        self.select_fn = select_fn
        self.toggle = toggle

preferences = [Preference("left_right_arrow_nav", "Left/Right Arrow Navigation", toggle_preference),
               Preference("clear_filter", "Auto Clear List Filters", toggle_preference),
               Preference("vim_mode", "Vim Mode", toggle_preference),
               Preference("dark_mode", "Dark Mode", toggle_preference),
               Preference("christmas_mode", "Christmas Theme", toggle_preference),
               Preference("browser_diff", "Open Diffs in Browser", toggle_preference),
               Preference("save_password", "Remember Password", password_toggle),
               Preference("editor", "Set Editor", set_editor_menu, False)
               ]

def draw_preferences():
    options = []
    for pref in preferences:
        if not pref.toggle:
            options.append(f"    {pref.description}")
        else:
            if is_preference_set(pref.name):
                options.append(f"[X] {pref.description}")
            else:
                options.append(f"[ ] {pref.description}")

    return options

def preferences_callback(selected_index):
    window = Window.get_window()

    pref = preferences[selected_index]
    pref.select_fn(pref.name)

    window.update_preferences()

def preferences_menu():
    window = Window.get_window()
    window.set_header(f"Preferences")

    window.create_list_popup("User Preferences", callback=preferences_callback, list_fill=draw_preferences)
