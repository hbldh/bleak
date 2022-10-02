==================
BleakScanner class
==================

.. autoclass:: bleak.BleakScanner


------------
Easy methods
------------

These methods and handy for simple programs but are not recommended for
more advanced use cases like long running programs, GUIs or connecting to
multiple devices.

.. automethod:: bleak.BleakScanner.discover
.. autoproperty:: bleak.BleakScanner.discovered_devices
.. automethod:: bleak.BleakScanner.find_device_by_address
.. automethod:: bleak.BleakScanner.find_device_by_filter


---------------------
Starting and stopping
---------------------

:class:`BleakScanner` is an context manager so the recommended way to start
and stop scanning is to use it in an ``async with`` statement::

    import asyncio
    from bleak import BleakScanner

    async def main():
        stop_event = asyncio.Event()

        # TODO: add something that calls stop_event.set()

        def callback(device, advertising_data):
            # TODO: do something with incoming data
            pass

        async with BleakScanner(callback) as scanner:
            ...
            # Important! Wait for an event to trigger stop, otherwise scanner
            # will stop immediately.
            await stop_event.wait()

        # scanner stops when block exits
        ...

    asyncio.run(main())


It can also be started and stopped without using the context manager using the
following methods:

.. automethod:: bleak.BleakScanner.start
.. automethod:: bleak.BleakScanner.stop


----------
Deprecated
----------

.. automethod:: bleak.BleakScanner.register_detection_callback
.. automethod:: bleak.BleakScanner.set_scanning_filter
.. automethod:: bleak.BleakScanner.get_discovered_devices
