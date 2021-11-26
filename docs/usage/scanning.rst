********
Scanning
********

.. note::

    You should always import the scanning class with ``from bleak import BleakScanner``. That way
    Bleak will select the appropriate backend implementation for your current OS.

The :class:`<BleakScanner> bleak.backends.scanner.BleakScanner` is the Bleak
class that is used to discover Bluetooth Low Energy devices by monitoring advertising data.

Simple scanning
===============

The simplest and most straightforward way to do a BLE scan
with Bleak is to use the :py:meth:`bleak.backends.scanner.BleakScanner.discover`
method on the :class:`<BleakScanner> bleak.backends.scanner.BleakScanner` class:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    async def main():
        # This will perform a scanning for 5 seconds, and the
        # program will continue after that duration.
        devices = await BleakScanner.discover(timeout=5.0)

        for d in devices:
            print(d)

    asyncio.run(main())

This will produce a printed list of detected devices:

.. code-block:: sh

    24:71:89:CC:09:05: CC2650 SensorTag
    4D:41:D5:8C:7A:0B: Apple, Inc. (b'\x10\x06\x11\x1a\xb2\x9b\x9c\xe3')


:py:meth:`bleak.backends.scanner.BleakScanner.discover` method returns instances of the
:py:class:`bleak.backends.device.BLEDevice` class. These can used e.g. for connecting to the devices
in question. This instance has ``name``, ``address`` and ``rssi`` attributes, as well as a ``metadata`` attribute, which is a
a dictionary with keys ``uuids`` and ``manufacturer_data``
which potentially contains a list of all service UUIDs on the device and a binary string of data from
the manufacturer of the device respectively.

In Windows and Linux, the peripherals are identified by a Bluetooth address (e.g. ``24:71:89:CC:09:05``), whereas
they are identified by a UUID that is unique for that peripheral on the specific computer that Bleak is run on.

..
    Add links to or write appropriate example files.

BleakScanner
============

The :class:`<BleakScanner> bleak.backends.scanner.BleakScanner` class
can also be used in the simple fashion described above, or in an asynchronous context manager way.

This program performs the exact same thing as the one above, but with the context manager
approach and a manual sleep call:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    async def main():
        # This asynchronous context manager starts the scanning on
        # entry to this scope and stops the scanning when exiting
        # the scope.
        async with BleakScanner() as scanner:
            # This sleep call keeps the scanning going for
            # the specified sleep duration.
            await asyncio.sleep(5.0)

        for d in scanner.discovered_devices:
            print(d)

    asyncio.run(main())

If you want to do the same thing with a :class:`<BleakScanner> bleak.backends.scanner.BleakScanner` instance
one can do this:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    async def main():
        scanner = BleakScanner()
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()

        for d in scanner.discovered_devices:
            print(d)

    asyncio.run(main())

..
    Add links to or write appropriate example files.

Custom detection callback
-------------------------

It is possible to customize the scanner class to perform actions of your own
choice upon receiving a new device update, in which none, some or all manufacturer data
might be sent as the second argument to the custom callback. The data sent as advertisment data
depends on the OS, what kind of device update it is and a lot of other things. Never assume that the
``advertisment_data`` always contains all the data available on the device.

.. code-block:: python

    import asyncio
    from bleak import BleakScanner, BLEDevice, AdvertisementData

    def custom_detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
        print(f"Custom callback: {device.address}, RSSI: {device.rssi}, Advertisement Data: {advertisement_data}")

    async def main():
        # This asynchronous context manager starts the scanning on
        # entry to this scope and stops the scanning when exiting
        # the scope.
        async with BleakScanner(detection_callback=custom_detection_callback) as scanner:
            # This sleep call keeps the scanning going for
            # the specified sleep duration.
            await asyncio.sleep(5.0)

        for d in scanner.discovered_devices:
            print(d)

    asyncio.run(main())

This will output something similar to:

.. code-block:: sh

    Custom callback: D9:39:84:D7:CF:8E, RSSI: -50, Advertisement Data: AdvertisementData(manufacturer_data={76: b'\x12\x02\x00\x01'})
    Custom callback: 5A:C6:8B:72:5C:7F, RSSI: -46, Advertisement Data: AdvertisementData(manufacturer_data={76: b'\x10\x06(\x1e&\xe1\x95\xe3'})
    Custom callback: 5A:C6:8B:72:5C:7F, RSSI: -46, Advertisement Data: AdvertisementData()
    Custom callback: 24:71:89:CC:09:05, RSSI: -44, Advertisement Data: AdvertisementData(manufacturer_data={13: b'\x03\x00\x00'}, service_uuids=['0000aa80-0000-1000-8000-00805f9b34fb'])
    Custom callback: 24:71:89:CC:09:05, RSSI: -44, Advertisement Data: AdvertisementData(local_name='CC2650 SensorTag')
    Custom callback: D9:39:84:D7:CF:8E, RSSI: -44, Advertisement Data: AdvertisementData(manufacturer_data={76: b'\x12\x02\x00\x01'})
    Custom callback: 5A:C6:8B:72:5C:7F, RSSI: -44, Advertisement Data: AdvertisementData(manufacturer_data={76: b'\x10\x06(\x1e&\xe1\x95\xe3'})
    Custom callback: 5A:C6:8B:72:5C:7F, RSSI: -43, Advertisement Data: AdvertisementData()
    Custom callback: 59:57:A3:79:54:75, RSSI: -53, Advertisement Data: AdvertisementData(manufacturer_data={76: b'\x10\x05\x05\x18(\xa5\xfa'})
    Custom callback: 59:57:A3:79:54:75, RSSI: -54, Advertisement Data: AdvertisementData()
    Custom callback: 5A:C6:8B:72:5C:7F, RSSI: -51, Advertisement Data: AdvertisementData(manufacturer_data={76: b'\x10\x06(\x1e&\xe1\x95\xe3'})
    Custom callback: 5A:C6:8B:72:5C:7F, RSSI: -51, Advertisement Data: AdvertisementData()
    D9:39:84:D7:CF:8E: Apple, Inc. (b'\x12\x02\x00\x01')
    5A:C6:8B:72:5C:7F: Apple, Inc. (b'\x10\x06(\x1e&\xe1\x95\xe3')
    24:71:89:CC:09:05: CC2650 SensorTag
    59:57:A3:79:54:75: Apple, Inc. (b'\x10\x05\x05\x18(\xa5\xfa')

.. todo::

    Add links to or write appropriate example files.

Scanning Filters
----------------

There are some pre-implemented scanning filters that can be used, and some capability to implement
own filtering methods as well.


Find specific device by address
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you already know the address of the peripheral that you want to detect by scanning, you can use the
:py:meth:`bleak.backends.scanner.BleakScanner.find_device_by_address` method:

.. code-block:: python

    import asyncio
    import platform
    import sys

    from bleak import BleakScanner

    async def main(address):
        device = await BleakScanner.find_device_by_address(address, timeout=10.0)
        print(device)


    if __name__ == "__main__":
        address = (
            "24:71:89:cc:09:05"  # <--- Change to your device's address here if you are using Windows or Linux
            if platform.system() != "Darwin"
            else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"  # <--- Change to your device's address here if you are using macOS
        )
        asyncio.run(main(address))

This will start scanning until a device with the address specified is found, or until 10 seconds has passed.
It is appropriate to use when you know the address of the peripheral and you only want to make the
OS detect it and make it connectable as fast as possible.

..
    Add links to or write appropriate example files.

Find devices by custom Bleak filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer to make filtering based on some other criteria than address, then this can be implemented
using detection callbacks in some cases as well. An example of filtering on the name of the peripheral instead of
the address:

.. code-block:: python

    import asyncio

    from bleak import BleakScanner


    async def main(wanted_name):
        device = await BleakScanner.find_device_by_filter(
            lambda d, ad: d.name and d.name.lower() == wanted_name.lower(), timeout=10.0
        )
        print(device)


    name = "CC2650 SensorTag"
    asyncio.run(main(name))

The program above will look for maximally 10 seconds for a device with the advertised name ``CC2650 SensorTag``
after which it will return ``None`` if nothing is found. If a device with a name that matches that string, then it will return that
a :py:class:`bleak.backends.device.BLEDevice` instance representing that peripheral.

See `scanner_byname.py <https://github.com/hbldh/bleak/blob/master/examples/scanner_byname.py>`_ for a more user-friendly
version of the above program.

Find devices by custom OS native filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can implement custom scanning filter that will reduce your scanning
results prior to them getting to bleak. These are still quite backend specific, but
they are generally used like this:

- On the `discover` method, send in keyword arguments according to what is
  described in the docstring of the method.
- On the backend's `BleakScanner` implementation, either send in keyword arguments
  according to what is described in the docstring of the class or use the
  ``set_scanning_filter`` method to set them after the instance has been created.

Scanning filters are currently implemented in Windows and BlueZ backends, but not yet
in the macOS backend. To filter there, you are forced to implement it yourself, using custom detection callbacks,
filtering after the scanning and similar.

Please note that they are not currently abstracted enough to be
OS independent. It is, at the moment, required to do some separate handling for each OS backend.

Scanning filter examples in .NET backend
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To be written. In the meantime, check docstrings
`here <https://github.com/hbldh/bleak/blob/master/bleak/backends/winrt/scanner.py#L43-L60>`_
and check out issue `#230 <https://github.com/hbldh/bleak/issues/230>`_.


Scanning filter examples in BlueZ backend
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To be written. In the meantime, check
`docstrings <https://github.com/hbldh/bleak/blob/master/bleak/backends/bluezdbus/scanner.py#L174-L183>`_.


Scanning filter examples in Core Bluetooth backend
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To be written. Exists in a draft in `PR #209 <https://github.com/hbldh/bleak/pull/209>`_.

Advertised data
---------------

TBW.
