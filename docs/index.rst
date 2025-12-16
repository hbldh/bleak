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


Operating System Support
------------------------

Bleak aims to work on most major operating systems via platform-specific backends.

Tier 1 support
~~~~~~~~~~~~~~

The following operating systems are supported and tested by the maintainers:

* Linux distributions with BlueZ >= 5.55
* Mac support via Core Bluetooth API, from at least macOS version 10.15
* Windows 10, version 16299 (Fall Creators Update) or greater

Tier 2 support
~~~~~~~~~~~~~~

The following operating systems are supported by the community, but not actively
tested by the maintainers:

* Android via Python4Android.

3rd party backends
~~~~~~~~~~~~~~~~~~

The following backends are implemented and maintained by 3rd parties:

* Bumble (a full Bluetooth stack implemented in Python) at `<https://github.com/vChavezB/bleak-bumble/>`_.
* ESPHome Bluetooth Proxy at `<https://github.com/Bluetooth-Devices/bleak-esphome>`_.
* Pythonista on iOS at `<https://github.com/o-murphy/bleak-pythonista>`_.


Features
--------

* Scan for devices advertising over BLE.
* Get name, service uuids, service data, manufacturer-specific data, transmit
  power and RSSI from advertising packets.
* Connect to BLE peripherals.
* Read and write GATT characteristics and descriptors.
* Subscribe to notifications/indications from characteristics.
* Initiate pairing/bonding with devices (platform dependent).

Contents:

.. toctree::
   :maxdepth: 2

   installation
   usage
   api/index
   backends/index
   troubleshooting
   contributing
   authors
   history

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
