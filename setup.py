"""Setup: For installation via PIP"""
import setuptools

from zygrader.config.shared import SharedData

VERSION_STR = SharedData.VERSION.vstring

setuptools.setup(
    name="zygrader",
    description="curses tool for zyBooks",
    version=VERSION_STR,
    author="Nathan Craddock",
    author_email="nzcraddock@gmail.com",
    url="https://github.com/natecraddock/zygrader",
    packages=setuptools.find_packages(),
    package_data={
        "": ["*.txt"],
    },
)
