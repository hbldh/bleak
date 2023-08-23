from setuptools import find_packages, setup

VERSION = "[VERSION]"  # Version will be filled in by the bleak recipe

# Package meta-data.
NAME = "bleak"
DESCRIPTION = "Bluetooth Low Energy platform Agnostic Klient"
URL = "https://github.com/hbldh/bleak"
EMAIL = "henrik.blidh@nedomkull.com"
AUTHOR = "Henrik Blidh"

# Where the magic happens:
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    packages=find_packages(exclude=("tests", "examples", "docs", "BleakUWPBridge")),
    entry_points={"console_scripts": ["bleak-lescan=bleak:cli"]},
    test_suite="tests",
    include_package_data=True,
    license="MIT",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "Topic :: Communications",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
    ]
)
