"""User: User preference window management"""
import base64
import sys

from zygrader import ui, zybooks
from zygrader.class_manager import download_roster
from zygrader.config import preferences
from zygrader.config.shared import SharedData
from zygrader.zybooks import Zybooks


def decode_password(password):
    """Decode a base64 encoded password"""
    decoded = base64.b64decode(password)
    return decoded.decode("utf-8")


def encode_password(password):
    """Encode a password in base64 for slight security"""
    return str(base64.b64encode(password.encode("ascii")), "utf-8")


def authenticate(window: ui.Window, zy_api: Zybooks, email, password):
    """Authenticate to the zyBooks api with the email and password."""
    def wait_fn():
        success = zy_api.authenticate(email, password)
        if success:
            download_roster(silent=True)
        return success

    popup = ui.layers.WaitPopup("Signing in")
    popup.set_message([f"Signing into zyBooks as {email}..."])
    popup.set_wait_fn(wait_fn)
    window.run_layer(popup)

    if popup.was_canceled():
        return False

    authenticated = popup.get_result()
    if not authenticated:
        popup = ui.layers.Popup("Error")
        popup.set_message(["Invalid Credentials"])
        window.run_layer(popup)
    return authenticated


def get_password(window: ui.Window):
    """Prompt for the user's password"""

    text_input = ui.layers.TextInputLayer(
        "Enter Password", mask=ui.components.TextInput.TEXT_MASKED)
    text_input.set_prompt(["Enter your zyBooks password"])
    window.run_layer(text_input, "Sign In")

    if text_input.was_canceled():
        return False

    return text_input.get_text()


# Create a user account
def create_account(window: ui.Window, zy_api):
    """Create zybooks user account info (email & password) in config"""

    while True:
        # Get user account information
        text_input = ui.layers.TextInputLayer("Enter Email")
        text_input.set_prompt(["Enter your zyBooks email"])
        window.run_layer(text_input, "Sign In")

        if text_input.was_canceled():
            return False

        email = text_input.get_text()
        password = get_password(window)
        if not password:
            return False

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
        authenticated = authenticate(window, zy_api, email, password)
        return authenticated

    # User does not have account created
    if not email:
        credentials = create_account(window, zy_api)
        if not credentials:
            return False

        email, password = credentials
        preferences.set("email", email)

        popup = ui.layers.BoolPopup("Save Password")
        popup.set_message(["Would you like to save your password?"])
        window.run_layer(popup)

        save_password = popup.get_result()
        if save_password:
            preferences.set("save_password", True)
            password = encode_password(password)
            preferences.set("password", password)
        else:
            preferences.set("save_password", False)

    # User has account (email), but has not saved their password.
    # Ask user for their password.
    elif not password:
        while True:
            password = get_password(window)
            if not password:
                return False

            if authenticate(window, zy_api, email, password):
                if preferences.get("save_password"):
                    password = encode_password(password)
                    preferences.set("password", password)
                break

    return True


def logout():
    """Log a user out by erasing their email and password from config"""
    window = ui.get_window()

    # Clear account information
    preferences.set("email", "")
    preferences.set("password", "")

    msg = [
        "You have been logged out. Would you like to sign in with different credentials?",
        "",
        "Answering `No` will quit zygrader.",
    ]
    popup = ui.layers.BoolPopup("Sign in?")
    popup.set_message(msg)

    sign_in = window.run_layer(popup)
    if sign_in:
        login(window)
    else:
        event_manager = ui.get_events()
        event_manager.push_zygrader_quit_event()


def save_password_toggle():
    """Toggle saving the user's password in their config file (encoded)"""
    if not preferences.get("save_password"):
        preferences.set("password", "")
    else:
        window = ui.get_window()
        popup = ui.layers.Popup("Remember Password")
        popup.set_message(
            ["Next time you start zygrader your password will be saved."])
        window.run_layer(popup)


class PreferenceToggle(ui.layers.Toggle):
    def __init__(self, name, extra_fn=None):
        super().__init__()
        self.__name = name
        self.__extra_fn = extra_fn
        self.get()

    def get(self):
        self._toggled = preferences.get(self.__name)

    def toggle(self):
        preferences.set(self.__name, not self._toggled)
        self.get()

        if self.__extra_fn:
            self.__extra_fn()


class StringRadioGroup(ui.layers.RadioGroup):
    def __init__(self, preference: str):
        self.__preference = preference

    def toggle(self, _id: str):
        preferences.set(self.__preference, _id)

    def is_toggled(self, _id: str):
        return preferences.get(self.__preference) == _id


class ThemeRadioGroup(ui.layers.RadioGroup):
    def __init__(self, preferences: list):
        self.__preferences = {pref: False for pref in preferences}

    def toggle(self, _id: str):
        for pref in self.__preferences:
            self.__preferences[pref] = False
        self.__preferences[_id] = True

    def is_toggled(self, _id: str):
        return self.__preferences[_id]


def preferences_menu():
    """Create the preferences popup"""
    window = ui.get_window()
    popup = ui.layers.ListLayer("User Preferences", popup=True)

    row = popup.add_row_parent("Appearance")
    row.add_row_toggle("Dark Mode", PreferenceToggle("dark_mode"))
    theme_radio = ThemeRadioGroup(["christmas_mode", "spooky_mode"])
    row.add_row_radio("Christmas Theme", theme_radio, "christmas_mode")
    row.add_row_radio("Spooky Theme", theme_radio, "spooky_mode")
    row.add_row_toggle("Unicode Mode", PreferenceToggle("unicode_mode"))

    row = popup.add_row_parent("Navigation")
    row.add_row_toggle("Vim Mode", PreferenceToggle("vim_mode"))
    row.add_row_toggle("Left/Right Arrow Navigation",
                       PreferenceToggle("left_right_arrow_nav"))
    row.add_row_toggle("Use Esc key to exit menus",
                       PreferenceToggle("use_esc_back"))

    # Editor selection submenu
    row = popup.add_row_parent("Text Editor")
    radio = StringRadioGroup("editor")
    for editor_name in preferences.EDITORS:
        row.add_row_radio(editor_name, radio, editor_name)

    row = popup.add_row_parent("Other")
    row.add_row_toggle("Auto Clear List Filters",
                       PreferenceToggle("clear_filter"))
    row.add_row_toggle("Open Diffs in Browser",
                       PreferenceToggle("browser_diff"))

    # Class code selector
    row = popup.add_row_parent("Class Code")
    radio = StringRadioGroup("class_code")
    class_codes = SharedData.get_class_codes()
    class_codes.insert(0, "No Override")
    for code in class_codes:
        row.add_row_radio(code, radio, code)

    row = popup.add_row_parent("Account")
    row.add_row_toggle("Remember Password",
                       PreferenceToggle("save_password", save_password_toggle))
    row.add_row_text("Log Out", logout)

    window.register_layer(popup, "Preferences")
