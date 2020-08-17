********
Scanning
********

Simple scanning
===============

To discover Bluetooth devices that can be connected to:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    async def main():
        devices = await BleakScanner.discover()
        for d in devices:
            print(d)

<<<<<<< HEAD:docs/advanced/scanning.rst
    asyncio.run(main())
=======
    asyncio.run(run())
>>>>>>> f8e1108 (First steps on docs rewrite.):docs/usage/scanning.rst

This will produce a printed list of detected devices:

.. code-block:: sh

    24:71:89:CC:09:05: CC2650 SensorTag
    4D:41:D5:8C:7A:0B: Apple, Inc. (b'\x10\x06\x11\x1a\xb2\x9b\x9c\xe3')


:py:meth:`bleak.backends.scanner.BleakScanner.discover` method returns instances of the
:py:class:`bleak.backends.device.BLEDevice` class. These can used e.g. for connecting to the devices
in question. This instance has ``name``, ``address`` and ``rssi`` attributes, as well as a ``metadata`` attribute,
a dict with keys ``uuids`` and ``manufacturer_data``
which potentially contains a list of all service UUIDs on the device and a binary string of data from
the manufacturer of the device respectively.

In Windows and Linux, the peripherals are identified by a Bluetooth address (e.g. ``24:71:89:CC:09:05``), whereas
they are identified by a UUID that is unique for that peripheral on the specific computer that Bleak is run on.


BleakScanner
============

The :class:`<BleakScanner> bleak.backends.scanner.BleakScanner` is the Bleak class that is used to discover
Bluetooth Low Energy devices by monitoring advertising data.

To discover Bluetooth devices that can be connected to:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    async def run():
        devices = await BleakScanner.discover(timeout=5.0)

        for d in devices:
            print(d)

    asyncio.run(run())

This will scan for 5 seconds and then produce a printed list of detected devices.

It can also be used as an object, either in an asynchronous context manager way:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    async def main():
        async with BleakScanner() as scanner:
            await asyncio.sleep(5.0)
<<<<<<< HEAD:docs/advanced/scanning.rst
        for d in scanner.discovered_devices:
            print(d)

    asyncio.run(main())
=======
            devices = await scanner.get_discovered_devices()

        for d in devices:
            print(d)

    asyncio.run(run())
>>>>>>> f8e1108 (First steps on docs rewrite.):docs/usage/scanning.rst

or separately, calling ``start`` and ``stop`` methods on the scanner manually:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

<<<<<<< HEAD:docs/advanced/scanning.rst
    def detection_callback(device, advertisement_data):
        print(device.address, "RSSI:", device.rssi, advertisement_data)

    async def main():
=======
    async def run():
>>>>>>> f8e1108 (First steps on docs rewrite.):docs/usage/scanning.rst
        scanner = BleakScanner()
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()

        for d in scanner.discovered_devices:
            print(d)

<<<<<<< HEAD:docs/advanced/scanning.rst
    asyncio.run(main())
=======
    asyncio.run(run())

The three examples above are equivalent in their results.

Detection callbacks
-------------------

It is possible to add your own callback that you want to call upon each
detected device:


.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    def my_detection_callback(device, advertisement_data):
        print(device.address, "RSSI:", device.rssi, advertisement_data)

    async def run():
        async with BleakScanner(detection_callback=my_detection_callback) as scanner:
            await asyncio.sleep(5.0)
            devices = await scanner.get_discovered_devices()

        for d in devices:
            print(d)

    asyncio.run(run())

or separately, calling ``start`` and ``stop`` methods on the scanner manually:

.. code-block:: python

    import asyncio
    from bleak import BleakScanner

    def my_detection_callback(device, advertisement_data):
        print(device.address, "RSSI:", device.rssi, advertisement_data)

    async def run():
        scanner = BleakScanner(detection_callback=my_detection_callback)
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()
        devices = await scanner.get_discovered_devices()

        for d in devices:
            print(d)
>>>>>>> f8e1108 (First steps on docs rewrite.):docs/usage/scanning.rst

    asyncio.run(run())


Scanning Filters
----------------

There are some scanning filters that can be applied, that will reduce your scanning
results prior to them getting to bleak. These are still quite backend specific, but
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

Advertised data
---------------

TBW.
