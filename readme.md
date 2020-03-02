# Zygrader
_Zygrader is a Python 3 ncurses tool to facilitate grading student submissions on the zyBooks online programming textbook system. It has been tested on Linux._

Zygrader is a tool developed for the BYU CS142 Introduction to Computer Programming teaching assistants by Nathan Craddock. Rather than navigating the slow zyBooks website to review student code, zygrader assists the grader in downloading, running, reviewing, and comparing student code.

### Setup
Zygrader is intended to be run from a shared folder. This has a few benefits
1. Everyone is running the same version
2. Data (cached files, lab and student data, locks, etc.) is shared. This could be done with a server-client model, but a shared codebase was determined to be the simplest result

### Code
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
