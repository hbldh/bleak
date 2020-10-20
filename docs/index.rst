bleak
=====

.. figure:: https://raw.githubusercontent.com/hbldh/bleak/master/Bleak_logo.png
    :target: https://github.com/hbldh/bleak
    :alt: Bleak Logo
    :width: 50%


.. image:: https://github.com/hbldh/bleak/workflows/Build%20and%20Test/badge.svg
    :target: https://github.com/hbldh/bleak/actions?query=workflow%3A%22Build+and+Test%22
    :alt: Build and Test

.. image:: https://img.shields.io/pypi/v/bleak.svg
    :target: https://pypi.python.org/pypi/bleak

.. image:: https://readthedocs.org/projects/bleak/badge/?version=latest
    :target: https://bleak.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Black


Bleak is an acronym for Bluetooth Low Energy platform Agnostic Klient.

* Free software: MIT license
* Documentation: https://bleak.readthedocs.io.

Bleak is a GATT client software, capable of connecting to BLE devices
acting as GATT servers. It is designed to provide a asynchronous,
cross-platform Python API to connect and communicate with e.g. sensors.


Features
--------

* Supports Windows 10, version 16299 (Fall Creators Update) or greater
* Supports Linux distributions with BlueZ >= 5.43 (See :ref:`linux-backend` for more details)
* OS X/macOS support via Core Bluetooth API, from at least OS X version 10.11

Bleak supports reading, writing and getting notifications from
GATT servers, as well as a function for discovering BLE devices.

Contents:

.. toctree::
   :maxdepth: 2

   installation
   scanning
   usage
   backends/index
   api
   troubleshooting
   contributing
   authors
   history

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
