# zygrader
_Zygrader is a Python 3 ncurses tool to facilitate grading student submissions on the zyBooks online programming textbook system. It has been tested on Linux._

Zygrader is a tool developed for the BYU CS142 Introduction to Computer Programming teaching assistants by Nathan Craddock, and others have since contributed to the project. Rather than navigating the slow zyBooks website to review student code, zygrader assists the grader in downloading, running, reviewing, and comparing student code.

Contents:
- [Installation](#installation)
- [User Manual](#user-manual)
- [Development](#development)
- [Code Documentation](#code-documentation)

# Installation

Zygrader is installed through `pip` for each user who each have their own local configuration stored at `~/.config/zygrader/config.json`. Each user
accesses a shared folder that can be stored at any location.

## Installation
```
# Install
$ python3 -m pip install https://github.com/natecraddock/zygrader/tarball/master

# Run
$ python3 -m zygrader

# Add alias to environment (works over SSH)
$ echo "alias zygrader='python3 -m zygrader'" >> ~/.bash_profile

# Then you can run as
$ zygrader
```

## Setup

Zygrader will not run without setting the data directory.
Each user will need to point zygrader to the shared folder by running

```
zygrader --set-data-dir [path]
```

Once it is set, it is stored in your user configuration.

To create the shared data folder (always named `.zygrader_data`), run zygrader with:

```
zygrader --init-data-dir [path]
```

For example

```
zygrader --init-data-dir /home/shared/programming/
```

will create the directory `/home/shared/programming/.zygrader_data/`.

# User Manual
As zygrader is a terminal application, all controls are entered with the keyboard.

The arrow keys can be used to navigate through lists of options, with enter to select.
Some parts of the interface also accept text input.

There is a vim mode which maps the `hjkl` keys to the arrow keys, with `i` and `ESC` to toggle between insert and normal mode.

# Development

Because zygrader is installed with `pip`, running `import zygrader` will first check for the system-wide install. This causes problems
for developing zygrader. To solve these issues, virtual environments are used.

Install virtualenv
```
$ python3 -m pip install --user virtualenv
```

Create the virtual environment
```
$ python3 -m venv ~/.virtualenvs/zygrader
```

Enter the virtual environment
```
$ source ~/.virtualenvs/zygrader/bin/activate
```

You must first install zygrader in _develop mode_ before running from source. Run the following from the zygrader repository.
```
$ pip install requests
$ pip install -e .
```

During development, zygrader should be run from the git repository.
```
$ python3 zygrader/main.py
```

To exit the virtual environment
```
deactivate
```

Each time you want to test the develop version you must be in the virtual environment. This prevents conflicts between the local and installed versions of zygrader.

Changes can be pushed to the git repository to share between developers. Zygrader checks GitHub for new tags when
it starts. If a commit has been tagged with a higher version number than the current version it will be downloaded
and installed.

## Pushing Updates
When enough features are ready, a major release can be sent to users. A major release includes:\
* updating the changelog `zygrader/config/changelog.txt`
* adding any needed versioning code in `zygrader/config/versioning.py`
* showing the changelog message in the versioning code (see previous versions)
* and update the version number in `zygrader/config/shared.py`.

If a critical bugfix release needs to be released (of the form `X.X1`, `X.X2`, ...), then the only needed change
is to update the version number in `zygrader/config/shared.py`.

## VSCode
After creating a virtual environment, you must select that as the python interpreter in VSCode for development. Enter the
command `Python: Select Interpreter` and choose the virtual environment. It searches the project folder and `~/.virtualenvs` for python environments so the venv may be created where desired.

### Debugging
VSCode can debug zygrader by including something similar to the following in `launch.json`

```
    "configurations": [
        {
            "name": "zygrader",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/zygrader/main.py",
            "console": "integratedTerminal"
        }
    ]
```

#### Tagging
After making necessary code changes, run `push_update.sh` with the new version number as the argument to tag and push the tag to the repository. After this runs successfully, any user who starts zygrader
will see it automatically download and update to the latest version. The argument to `push_update.sh` should match the
VERSION variable in `shared.py` exactly.

**Example:** _pushing a major version 3.6_
```
$ ./push_update.sh 3.6
```

**Example:** _pushing a buxfix update to version 3.5_
```
$ ./push_update.sh 3.51
```

# Code Documentation
This is an overview of the files in the `zygrader` directory:
```
├── LICENSE
├── push_update.sh            - Script to help push release updates to users
├── readme.md
├── setup.py                  - Configuration for pip installation
├── readme.md
└── zygrader
    ├── admin.py              - The base admin submenu and basic commands
    ├── class_manager.py      - The menus to add classes and edit labs
    ├── config
    │   ├── changelog.txt     - Used to show version updates in the UI
    │   ├── shared.py         - Shared configuration data
    │   ├── __init__.py
    │   ├── user.py           - User configuration data
    │   └── versioning.py     - For making changes on new versions
    ├── data
    │   ├── flags.py          - For flagging labs
    │   ├── fs_watch.py       - A module that creates a file watcher thread
    │   ├── __init__.py
    │   ├── lock.py           - For locking labs
    │   ├── model.py          - Student, Lab, and Submission classes
    ├── grade_puller.py       - To pull grades from canvas into csv files
    ├── grader.py             - Grading menus and functions
    ├── __init__.py
    ├── logger.py             - A basic logger for debugging
    ├── ui
    │   ├── components.py     - Classes for various reusable UI components that are shown in the window
    │   ├── __init__.py
    │   ├── utils.py          - Shared windowing utility functions
    │   └── window.py         - A threaded window manager for event and component management
    ├── utils.py              - Shared functions (diffing, thread blocking)
    ├── zybooks.py            - zyBooks API wrapper
    └── main.py               - Creates the main menu & starts zygrader, argument parsing, signals
```

An overview of the more complex modules follows.

---

## Window Manager - `window.py`
The Window manager provides a simple event-driven user interface, with a separate thread for reading events from the keyboard. It uses the Python [ncurses](https://docs.python.org/3/library/curses.html#module-curses) wrapper.

### **`class Event`**
The Event class is a pure data structure to associate an event type, value, and modifier. It also contains constants for event types (NONE, BACKSPACE, ENTER, UP, ...).

### **`class WinContext`**
Another pure data structure to store the Window, Event, active component, and any custom data when executing a callback. This keeps callback arguments to a minimum.

### **`class Window`**
This class drives most of the behavior of zygrader. The file is relatively well-documented, a high level overview is given here.

The Window class is split between two threads (messy!), the main drawing thread and the input thread. The input thread runs a loop using the ncurses `window.getch()` in nodelay mode where input does not block. Any caught events are packaged into an `Event` object and placed into the `self.event_queue` which is a thread-safe shared queue structure. The draw thread waits (blocks) until an event is found in the queue.

The draw thread is managed by the `create_*` functions, which create the various components of the interface that accept user input.

#### `get_window()`
The `Window` class is a singleton, so this may be used anywhere in the code to access the current Window.

#### `input_thread_fn()`
The callback for the input thread. An empty curses window is created for reading input. Input is read in a loop calling `get_input()`, and any captured events are placed in the queue.

#### `get_input() / get_input_vim()`
This reads the input. If no input is read an Event of type NONE is returned. Otherwise the input code is read and the corresponding Event object is returned. If Vim keybindings are enabled, the `get_input_vim()` function will be called to handle that special case.

#### `consume_event()`
Called from the draw thread. Blocks when no events are in the queue.

#### `push_refresh_event()`
To be used from the draw thread to force a UI redraw

#### `__init_curses()`
The `curses.wrapper` function is used here to automatically handle cleanup of curses when zygrader exits. This calls the callback (which is `zygrader.py main()`) after initializing some basic window/curses settings.

#### `draw()`
This is called to draw the components. The active components are stored in a stack and drawn bottom to top. The entire screen is erased, then each component's `draw()` function is called. Finally we use `curses.doupdate()` which paints the final screen to the terminal. This is better than using `window.refresh()` in each component which causes jitter and flickering.

#### `create_*()` functions
Each component has at least one `create_*()` function which instantiates an instance, and begins an event loop for the component. Each calls `component_init()` and `component_deinit()` to add and remove it from the stack. For example, `create_bool_popup` creates an OptionsPopup with the fixed options of "Yes" and "No". A loop is run waiting for specific events. These events call functions on the popup. The loop runs until an option is selected, after which the function returns the True/False chosen value.

These vary in complexity, but all follow the same general design.

---

## zyBooks API - `zybooks.py`
The zyBooks API is a small wrapper around some zyBooks webpage-building requests. The [zyBooks website](https://learn.zybooks.com/) is created with the Ember.js framework, which builds the page locally with JSON responses. If anything breaks in zygrader in the future, it will be the wrapper around their API (which isn't publicly documented).

To find the API urls, open zyBooks in a browser with the network traffic inspector open. An example will be given to locate the URL for downloading a student's submissions. Find the *Lab Statistics and submissions* box on the page and pick a student from the list. At the time of writing, two identical requests are sent to `https://zyserver.zybooks.com/v1/zybook/[BOOK CODE]/programming_submission/[SECTION CODE]/user/[USER ID]?auth_token=XXXX`. The `BOOK CODE` is the name of the book, for example BYUCS142Spring2020. The `SECTION CODE` is a number unique to the page (section) in zyBooks. Finally, the `USER ID` is the user's id. (The function `zybooks.py get_roster()` downloads the JSON for all of the students in a book).

If anything in zyBooks breaks regarding the zyBooks integration (downloading submissions, logging in), the first thing I would do is check if their API urls have changed.

ZyBooks submission responses contain links to zip files stored on Amazon's AWS.

### **`class Zybooks`**
The Zybooks class has a static field `session` that stores the `requests` session. Each instantiated object has access to this session which stores the auth token and allows subsequent requests access.

#### `authenticate()`
Accepts a username and password string to authenticate the user. It is run automatically when zygrader is executed.

#### `download_assignment()`
Assignments (created with the Class Manager) can have multiple "parts" within them. This is to allow multi-section assignments like midterms. This iterates through each part in the assignment and downloads the submission JSON from zyBooks.

#### `get_submission_zip()`
Download the submission at the given URL, or from the local cache if available. Zygrader automatically caches each downloaded submission (.zip), so this function will check there first.
