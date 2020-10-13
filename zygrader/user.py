"""User: User preference window management"""
import base64
from queue import Queue
import sys

from zygrader.zybooks import Zybooks
from zygrader.config.shared import SharedData
from zygrader import zybooks

from zygrader.class_manager import download_roster
from zygrader.config import preferences
from zygrader import data
from zygrader import ui


def decode_password(password):
    """Decode a base64 encoded password"""
    decoded = base64.b64decode(password)
    return decoded.decode("utf-8")


def encode_password(password):
    """Encode a password in base64 for slight security"""
    return str(base64.b64encode(password.encode("ascii")), "utf-8")


def authenticate(window: ui.Window, zy_api: Zybooks, email, password):
    """Authenticate to the zyBooks api with the email and password."""
    def wait_fn(queue: Queue):
        success = zy_api.authenticate(email, password)
        if success:
            download_roster(silent=True)
        return success

    popup = ui.layers.WaitPopup("Signing in")
    popup.set_message([f"Signing into zyBooks as {email}..."])
    popup.set_wait_fn(wait_fn)
    window.run_layer(popup)

    authenticated = popup.result
    if not authenticated:
        popup = ui.layers.Popup("Error")
        popup.set_message(["Invalid Credentials"])
        window.run_layer(popup)
    return authenticated


def get_password(window: ui.Window):
    """Prompt for the user's password"""
    window.set_header("Sign In")

    text_input = ui.layers.TextInputLayer(
        "Enter Password", mask=ui.components.TextInput.TEXT_MASKED)
    text_input.set_prompt("Enter your zyBooks password")
    window.run_layer_for_result(text_input)

    password = text_input.text
    if password == ui.Window.CANCEL:
        password = ""

    return password


# Create a user account
def create_account(window: ui.Window, zy_api):
    """Create zybooks user account info (email & password) in config"""
    window.set_header("Sign In")

    while True:
        # Get user account information
        text_input = ui.layers.TextInputLayer("Enter Email")
        text_input.set_prompt("Enter your zyBooks email")
        window.run_layer_for_result(text_input)

        email = text_input.text
        if email == ui.Window.CANCEL:
            email = ""
        password = get_password(window)

        if authenticate(window, zy_api, email, password):
            break

    return email, password


def login(window: ui.Window):
    """Authenticate to zybooks with the user's email and password
    or create an account if one does not exist"""
    zy_api = zybooks.Zybooks()

    email = preferences.get("email")
    password = preferences.get("password")

    # If user email and password exist, authenticate and return
    if email and password:
        password = decode_password(password)
        authenticate(window, zy_api, email, password)
        window.set_email(email)
        return

    # User does not have account created
    if not email:
        email, password = create_account(window, zy_api)
        preferences.set("email", email)

        popup = ui.layers.BoolPopup("Save Password")
        popup.set_message(["Would you like to save your password?"])
        window.run_layer_for_result(popup)

        save_password = popup.get_result()
        if save_password:
            preferences.set("save_password", True)
            password = encode_password(password)
            preferences.set("password", password)

        window.set_email(email)

    # User has account (email), but has not saved their password.
    # Ask user for their password.
    elif not password:
        while True:
            password = get_password(window)

            if authenticate(window, zy_api, email, password):
                if preferences.get("save_password"):
                    password = encode_password(password)
                    preferences.set("password", password)
                break


def logout():
    """Log a user out by erasing their email and password from config"""
    preferences.set("email", "")
    preferences.set("password", "")

    window = ui.get_window()
    msg = [
        "You have been logged out. Would you like to sign in with different credentials?",
        "",
        "Answering `No` will quit zygrader.",
    ]
    sign_in = window.create_bool_popup("Sign in?", msg)

    if sign_in:
        login(window)
    else:
        sys.exit()


def draw_text_editors():
    """Draw the list of text editors"""
    options = []
    current_editor = preferences.get("editor")

    for name in preferences.EDITORS:
        if current_editor == name:
            options.append(f"[X] {name}")
        else:
            options.append(f"[ ] {name}")

    return options


def set_editor(editor_index, pref_name):
    """Set the user's default editor to the selected editor"""
    editor = list(preferences.EDITORS.keys())[editor_index]
    preferences.set(pref_name, editor)


def set_editor_menu(name):
    """Open the set editor popup"""
    window = ui.get_window()
    edit_fn = lambda context: set_editor(context.data, name)
    window.create_list_popup("Set Editor",
                             callback=edit_fn,
                             list_fill=draw_text_editors)


def draw_class_codes():
    """Draw the list of class codes"""
    class_codes = SharedData.get_class_codes()
    class_codes.insert(0, "No Override")
    current_code = preferences.get("class_code")

    options = []
    for code in class_codes:
        if current_code == code:
            options.append(f"[X] {code}")
        else:
            options.append(f"[ ] {code}")
    return options


def set_class_code_override(code_index: int, pref_name: str):
    """Set the current class code to the user's overridden code"""
    class_codes = SharedData.get_class_codes()
    class_codes.insert(0, "No Override")

    preferences.set(pref_name, class_codes[code_index])

    # Update all data to use the new class code
    SharedData.initialize_shared_data(SharedData.ZYGRADER_DATA_DIRECTORY)
    data.load_students()
    data.load_labs()
    data.load_class_sections()


def set_class_code_override_menu(pref_name: str):
    """Open the set class code override popup"""
    window = ui.get_window()
    set_fn = lambda context: set_class_code_override(context.data, pref_name)
    window.create_list_popup("Override Class Code",
                             callback=set_fn,
                             list_fill=draw_class_codes)


def toggle_preference(pref):
    """Toggle a boolean preference"""
    current_value = preferences.get(pref)
    preferences.set(pref, not current_value)


def save_password_toggle(preference_name):
    """Toggle saving the user's password in their config file (encoded)"""
    toggle_preference(preference_name)

    if not preferences.get(preference_name):
        preferences.set("password", "")
    else:
        window = ui.get_window()
        window.create_popup(
            "Remember Password",
            ["Next time you start zygrader your password will be saved."],
        )


# Preference types
# Toggle for booleans
# Menu for submenus
# Action for 1 time actions
PREFERENCE_TOGGLE = 1
PREFERENCE_MENU = 2
PREFERENCE_ACTION = 3


class Preference:
    """Holds information for a user preference item"""
    def __init__(self, name, description, select_fn, _type=PREFERENCE_TOGGLE):
        self.name = name
        self.description = description
        self.select_fn = select_fn
        self.type = _type


PREFERENCES = [
    Preference("left_right_arrow_nav", "Left/Right Arrow Navigation",
               toggle_preference),
    Preference("use_esc_back", "Use Esc key to exit menus", toggle_preference),
    Preference("clear_filter", "Auto Clear List Filters", toggle_preference),
    Preference("vim_mode", "Vim Mode", toggle_preference),
    Preference("dark_mode", "Dark Mode", toggle_preference),
    Preference("christmas_mode", "Christmas Theme", toggle_preference),
    Preference("browser_diff", "Open Diffs in Browser", toggle_preference),
    Preference("save_password", "Remember Password", save_password_toggle),
    Preference(
        "class_code",
        "Override Class Code",
        set_class_code_override_menu,
        PREFERENCE_MENU,
    ),
    Preference("editor", "Set Editor", set_editor_menu, PREFERENCE_MENU),
    Preference("log_out", "Log Out", logout, PREFERENCE_ACTION),
]


def draw_preferences():
    """Create the list of user preferences"""
    options = []
    for pref in PREFERENCES:
        if pref.type in {PREFERENCE_MENU, PREFERENCE_ACTION}:
            options.append(f"    {pref.description}")
        else:
            if preferences.get(pref.name):
                options.append(f"[X] {pref.description}")
            else:
                options.append(f"[ ] {pref.description}")

    return options


def preferences_callback(context: ui.WinContext):
    """Callback to run when a preference is selected"""
    selected_index = context.data
    pref = PREFERENCES[selected_index]

    if pref.type in {PREFERENCE_MENU, PREFERENCE_TOGGLE}:
        pref.select_fn(pref.name)
    else:
        pref.select_fn()


def preferences_menu():
    """Create the preferences popup"""
    window = ui.get_window()
    window.set_header(f"Preferences")

    window.create_list_popup("User Preferences",
                             callback=preferences_callback,
                             list_fill=draw_preferences)
