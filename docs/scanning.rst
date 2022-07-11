=============
Scan/Discover
=============

BleakScanner
------------

The :class:`<BleakScanner> bleak.backends.scanner.BleakScanner` class is used to discover
Bluetooth Low Energy devices by monitoring advertising data.

To discover Bluetooth devices that can be connected to:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    async def main():
        devices = await BleakScanner.discover()
        for d in devices:
            print(d)

    asyncio.run(main())

.. warning:: Do not name your script `bleak.py`! It will cause a circular import error.

.. warning:: On macOS you may need to give your terminal permission to access Bluetooth.
    See `this troubleshooting message <https://bleak.readthedocs.io/en/latest/troubleshooting.html#bleak-crashes-with-sigabrt-on-macos>`_


This will scan for 5 seconds and then produce a printed list of detected devices::

    24:71:89:CC:09:05: CC2650 SensorTag
    4D:41:D5:8C:7A:0B: Apple, Inc. (b'\x10\x06\x11\x1a\xb2\x9b\x9c\xe3')

The first part, a Bluetooth address in Windows and Linux and a UUID in macOS, is what is
used for connecting to a device using Bleak. The list of objects returned by the `discover`
method are instances of :py:class:`bleak.backends.device.BLEDevice` and has ``name``, ``address``
and ``rssi`` attributes, as well as a ``metadata`` attribute, a dict with keys ``uuids`` and ``manufacturer_data``
which potentially contains a list of all service UUIDs on the device and a binary string of data from
the manufacturer of the device respectively.

It can also be used as an object, either in an asynchronous context manager way:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    async def main():
        async with BleakScanner() as scanner:
            await asyncio.sleep(5.0)
        for d in scanner.discovered_devices:
            print(d)

    asyncio.run(main())

or separately, calling ``start`` and ``stop`` methods on the scanner manually:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    def detection_callback(device, advertisement_data):
        print(device.address, "RSSI:", device.rssi, advertisement_data)

    async def main():
        scanner = BleakScanner(detection_callback)
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()

        for d in scanner.discovered_devices:
            print(d)

    asyncio.run(main())

In the manual mode, it is possible to add an own callback that you want to call upon each
scanner detection, as can be seen above. There are also possibilities of adding scanning filters,
which differ widely between OS backend implementations, so the instructions merit careful reading.


Scanning Filters
----------------

There are some scanning filters that can be applied, that will reduce your scanning
results prior to them getting to bleak. These are quite backend specific, but
they are generally used like this:

- On the `discover` method, send in keyword arguments according to what is
  described in the docstring of the method.
- On the backend's `BleakScanner` implementation, either send in keyword arguments
  according to what is described in the docstring of the class or use the
  ``set_scanning_filter`` method to set them after the instance has been created.

Scanning filters are currently implemented in Windows and BlueZ backends, but not yet
in the macOS backend.

Scanning filter examples in .NET backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To be written. In the meantime, check docstrings
`here <https://github.com/hbldh/bleak/blob/master/bleak/backends/winrt/scanner.py#L43-L60>`_
and check out issue `#230 <https://github.com/hbldh/bleak/issues/230>`_.


Scanning filter examples in BlueZ backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To be written. In the meantime, check
`docstrings <https://github.com/hbldh/bleak/blob/master/bleak/backends/bluezdbus/scanner.py#L174-L183>`_.


Scanning filter examples in Core Bluetooth backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To be implemented. Exists in a draft in `PR #209 <https://github.com/hbldh/bleak/pull/209>`_.
