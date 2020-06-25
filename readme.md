# zygrader
_Zygrader is a Python 3 ncurses tool to facilitate grading student submissions on the zyBooks online programming textbook system. It has been tested on Linux._

Zygrader is a tool developed for the BYU CS142 Introduction to Computer Programming teaching assistants by Nathan Craddock, and others have since contributed to the project. Rather than navigating the slow zyBooks website to review student code, zygrader assists the grader in downloading, running, reviewing, and comparing student code.

Contents:
- [Installation](#installation)
- [User Manual](#user-manual)
- [Code Documentation](#code-documentation)

# Installation

## Design Paradigm
Zygrader is intended to be run from a shared folder, rather than through per-user install. This has a few benefits
1. Everyone is running the same version always
2. Data (cached files, lab and student data, locks, etc.) is shared. This could be done with a server-client model, but a shared codebase was determined to be the simplest approach.

Because of this, there is a pseudo-installer, which really creates a symbolic link to the shared module.

## Global Installation

In the shared folder, clone the git directory. For example, if the shared folder is called `zybooks_grading`:

```
$ mkdir ~/zybooks_grading && cd ~/zybooks_grading
$ git clone https://github.com/natecraddock/zygrader
```

Copy the `install.sh` file to a path that all graders have access to.

```
$ cp ~/zybooks_grading/zygrader/install.sh ~/zybooks_grading/install.sh
```

Make sure to properly set the INSTALL_PATH variable (see the note in `install.sh`)

## User Installation

The above needs to happen only once. Instruct users to run `install.sh`. This makes a symbolic link between a `zygrader` file on the desktop and the `__main__.py` file. Make sure that users do not have write access to `__main__.py`. A `zygrader` command is also added to the user's `$PATH`.

Run `zygrader` from a terminal after installation.

Run `python3 zygrader -a` to enable admin mode, which gives access to the admin menu for class management and other less-used features.

# User Manual
As zygrader is a terminal application, all controls are entered with the keyboard.

The arrow keys can be used to navigate through lists of options, with enter to select.
Some parts of the interface also accept text input.

There is a vim mode which maps the `hjkl` keys to the arrow keys, with `i` and `ESC` to toggle between insert and normal mode.

# Code Documentation
This is an overview of the files in the `zygrader` directory:
```
├── install.sh                - The pseudo-installer for users; creates a symbolic link
├── LICENSE
├── __main__.py               - The main file where the zygrader module runs from
├── readme.md
└── zygrader
    ├── admin.py              - The base admin submenu and basic commands
    ├── class_manager.py      - The menus to add classes and edit labs
    ├── config
    │   ├── changelog.txt     - Used to show version updates in the UI
    │   ├── g_data.py         - Global configuration data
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
    └── zygrader.py           - Creates the main menu (called from __main__.py)
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
