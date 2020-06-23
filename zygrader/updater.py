"""Updater: To auto-update zygrader during runtime"""
import requests
import subprocess
import sys

from zygrader.config.shared import SharedData

REPO_NAME = "natecraddock/zygrader"
API_URL = f"https://api.github.com/repos/{REPO_NAME}/tags"

def get_latest_version():
    """Check the zygrader git repo tags for a new version"""
    r = requests.get(API_URL)
    if not r.ok:
        return SharedData.VERSION

    latest = float(r.json()[0]["name"])
    if latest > SharedData.VERSION:
        return latest

    return SharedData.VERSION

def update_zygrader(latest_version):
    """Download zygrader from the git repository and update it"""
    print()
    print(f"Updating zygrader [{SharedData.VERSION} -> {latest_version}]")
    print()

    # Get tarball URL from github
    r = requests.get(API_URL)
    if not r.ok:
        print("Failed to download latest version.")
        sys.exit()

    tag = r.json()[0]
    tarball_url = tag["tarball_url"]

    # Install the new version of zygrader
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "--user", "--upgrade", "--no-cache-dir", tarball_url])
    except subprocess.CalledProcessError:
        print("Failed to update zygrader. Exiting")
        print()
        return

    print("zygrader successfully updated. Please run zygrader again.")
