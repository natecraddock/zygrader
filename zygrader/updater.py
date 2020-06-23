"""Updater: To auto-update zygrader during runtime"""
import requests
import subprocess
import sys

from . import config

REPO_NAME = "natecraddock/zygrader"
API_URL = f"https://api.github.com/repos/{REPO_NAME}/tags"
INSTALL_URL = f"https://github.com/{REPO_NAME}/tarball/master"

def get_latest_version():
    """Check the zygrader git repo tags for a new version"""
    r = requests.get(API_URL)
    if not r.ok:
        return config.g_data.VERSION

    latest = float(r.json()[0]["name"])
    if latest > config.g_data.VERSION:
        return latest

    return config.g_data.VERSION

def update_zygrader(latest_version):
    """Download zygrader from the git repository and update it"""
    print()
    print(f"Updating zygrader [{config.g_data.VERSION} -> {latest_version}]")
    print()

    # Install the new version of zygrader
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", INSTALL_URL])
    except subprocess.CalledProcessError:
        print("Failed to update zygrader. Exiting")
        print()
        return

    # zygrader updated properly, fork and run zygrader again
    # TODO: Update here once zygrader is a package
