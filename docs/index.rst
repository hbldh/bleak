bleak
=====

.. image:: https://www.dropbox.com/s/fm0670e9yrmwr5t/Bleak_logo.png?raw=1
    :target: https://github.com/hbldh/bleak
    :alt: Bleak Logo
    :width: 50%

|

.. image:: https://dev.azure.com/hbldh/github/_apis/build/status/hbldh.bleak?branchName=master
    :target: https://dev.azure.com/hbldh/github/_build/latest?definitionId=4&branchName=master

.. image:: https://img.shields.io/pypi/v/bleak.svg
    :target: https://pypi.python.org/pypi/bleak

.. image:: https://readthedocs.org/projects/bleak/badge/?version=latest
    :target: https://bleak.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://pyup.io/repos/github/hbldh/bleak/shield.svg
     :target: https://pyup.io/repos/github/hbldh/bleak/
     :alt: Updates


Bleak is an acronym for Bluetooth Low Energy platform Agnostic Klient.

* Free software: MIT license
* Documentation: https://bleak.readthedocs.io.

Bleak is a GATT client software, capable of connecting to BLE devices
acting as GATT servers. It is designed to provide a asynchronous,
cross-platform Python API to connect and communicate with e.g. sensors.

**Be warned: Bleak is still in an early state of implementation.**

Features
--------

* Supports Windows 10, version 16299 (Fall Creators Update)
* Supports Linux distributions with BlueZ >= 5.43
* Plans on macOS support via Core Bluetooth API (see `develop` branch for progress)

Bleak supports reading, writing and getting notifications from
GATT servers, as well as a function for discovering BLE devices.

Contents:

.. toctree::
   :maxdepth: 2

   installation
   usage
   backends/index
   api
   contributing
   authors
   history

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
