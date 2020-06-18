# zygrader
_Zygrader is a Python 3 ncurses tool to facilitate grading student submissions on the zyBooks online programming textbook system. It has been tested on Linux._

Zygrader is a tool developed for the BYU CS142 Introduction to Computer Programming teaching assistants by Nathan Craddock, and others have since contributed to the project. Rather than navigating the slow zyBooks website to review student code, zygrader assists the grader in downloading, running, reviewing, and comparing student code.

Contents:
- [Installation](#installation)
- [Features](#features)
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

# Features


# User Manual
As zygrader is a terminal application, all controls are entered with the keyboard.

The arrow keys can be used to navigate through lists of options, with enter to select.
Some parts of the interface also accept text input.

There is a vim mode which maps the `hjkl` keys to the arrow keys, with `i` and `ESC` to toggle between insert and normal mode.

# Code Documentation
This is an overview of the files in the `zygrader` directory:
```
├── install.sh              | The pseudo-installer for users; creates a symbolic link
├── LICENSE
├── __main__.py             | The main file where the zygrader module runs from
├── readme.md
└── zygrader
    ├── admin.py            | The base admin submenu and basic commands
    ├── class_manager.py    | The menus to add classes and edit labs
    ├── config
    │   ├── changelog.txt   | Used to show version updates in the UI
    │   ├── g_data.py       | Global configuration data
    │   ├── __init__.py
    │   ├── user.py         | User configuration data
    │   └── versioning.py   | For making changes on new versions
    ├── data
    │   ├── flags.py        | For flagging labs
    │   ├── fs_watch.py     | A module that creates a file watcher thread
    │   ├── __init__.py
    │   ├── lock.py         | For locking labs
    │   ├── model.py        | Student, Lab, and Submission classes
    ├── grade_puller.py     | To pull grades from canvas into csv files
    ├── grader.py           | Grading menus and functions
    ├── __init__.py
    ├── logger.py           | A basic logger for debugging
    ├── ui
    │   ├── components.py   | Classes for various reusable UI components that are shown in the window
    │   ├── __init__.py
    │   ├── utils.py        | Shared windowing utility functions
    │   └── window.py       | A threaded window manager for event and component management
    ├── utils.py            | Shared functions (diffing, thread blocking)
    ├── zybooks.py          | zyBooks API wrapper
    └── zygrader.py         | Creates the main menu (called from __main__.py)
```
