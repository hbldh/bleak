=====
bleak
=====

.. image:: https://www.dropbox.com/s/fm0670e9yrmwr5t/Bleak_logo.png?raw=1
    :target: https://github.com/hbldh/bleak
    :alt: Bleak Logo
    :scale: 50%

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

Installation
------------

.. code-block:: bash

    $ pip install bleak

Features
--------

* Supports Windows 10, version 16299 (Fall Creators Update) or greater
* Supports Linux distributions with BlueZ >= 5.43
* Plans on macOS support via Core Bluetooth API (see `develop` branch for progress)

Bleak supports reading, writing and getting notifications from
GATT servers, as well as a function for discovering BLE devices.

Usage
-----

To discover Bluetooth devices that can be connected to:

.. code-block:: python

    import asyncio
    from bleak import discover

    async def run():
        devices = await discover()
        for d in devices:
            print(d)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())


Connect to a Bluetooth device and read its model number:

.. code-block:: python

    import asyncio
    from bleak import BleakClient

    address = "24:71:89:cc:09:05"
    MODEL_NBR_UUID = "00002a24-0000-1000-8000-00805f9b34fb"

    async def run(address, loop):
        async with BleakClient(address, loop=loop) as client:
            model_number = await client.read_gatt_char(MODEL_NBR_UUID)
            print("Model Number: {0}".format("".join(map(chr, model_number))))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(address, loop))


See examples folder for more code, among other example code for connecting to a
`TI SensorTag CC2650 <http://www.ti.com/ww/en/wireless_connectivity/sensortag/>`_
