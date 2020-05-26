# zygrader
_Zygrader is a Python 3 ncurses tool to facilitate grading student submissions on the zyBooks online programming textbook system. It has been tested on Linux._

Zygrader is a tool developed for the BYU CS142 Introduction to Computer Programming teaching assistants by Nathan Craddock. Rather than navigating the slow zyBooks website to review student code, zygrader assists the grader in downloading, running, reviewing, and comparing student code.

Contents:
- [Installation](#installation)
- [Features](#features)
- [User Manual](#user-manual)
- [Code Documentation](#code-documentation)

# Installation

## Design Paradigm
Zygrader is intended to be run from a shared folder, rather than through per-user install. This has a few benefits
1. Everyone is running the same version always
2. Data (cached files, lab and student data, locks, etc.) is shared. This could be done with a server-client model, but a shared codebase was determined to be the simplest result

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


# Code Documentation
This is an overview of the files in the `zygrader` directory.
```
├── admin.py
├── class_manager.py
├── config
│   ├── g_data.py
│   ├── __init__.py
│   ├── user.py
│   └── versioning.py
├── data
│   ├── __init__.py
│   ├── lock.py
│   └── model.py
├── grader.py
├── __init__.py
├── logger.py
├── ui
│   ├── components.py
│   ├── __init__.py
│   ├── utils.py
│   └── window.py
├── zybooks.py
└── zygrader.py
```
