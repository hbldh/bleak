#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command

# Package meta-data.
NAME = "bleak"
DESCRIPTION = "Bluetooth Low Energy platform Agnostic Klient"
URL = "https://github.com/hbldh/bleak"
EMAIL = "henrik.blidh@nedomkull.com"
AUTHOR = "Henrik Blidh"

REQUIRED = [
    "typing-extensions>=4.2.0",
    # Linux reqs
    'dbus-next;platform_system=="Linux"',
    # macOS reqs
    'pyobjc-core;platform_system=="Darwin"',
    'pyobjc-framework-CoreBluetooth;platform_system=="Darwin"',
    'pyobjc-framework-libdispatch;platform_system=="Darwin"',
    # Windows reqs
    'bleak-winrt>=1.1.1;platform_system=="Windows"',
]

here = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = "\n" + f.read()

# Load the package's __version__.py module as a dictionary.
about = {}
with open(os.path.join(here, NAME, "__version__.py")) as f:
    exec(f.read(), about)


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPi via Twine…")
        os.system("twine upload dist/*")

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=find_packages(exclude=("tests", "examples", "docs", "BleakUWPBridge")),
    entry_points={"console_scripts": ["bleak-lescan=bleak:cli"]},
    install_requires=REQUIRED,
    test_suite="tests",
    include_package_data=True,
    license="MIT",
    project_urls={
        "Changelog": "https://github.com/hbldh/bleak/blob/develop/CHANGELOG.rst",
        "Documentation": "https://bleak.readthedocs.io",
        "Support": "https://github.com/hbldh/bleak/discussions",
        "Issues": "https://github.com/hbldh/bleak/issues",
    },
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Android",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    # $ setup.py publish support.
    cmdclass={"upload": UploadCommand},
)
