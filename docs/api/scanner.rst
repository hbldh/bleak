==================
BleakScanner class
==================

.. py:currentmodule:: bleak

.. autoclass:: bleak.BleakScanner


------------
Easy methods
------------

These methods and handy for simple programs but are not recommended for
more advanced use cases like long running programs, GUIs or connecting to
multiple devices.

.. automethod:: bleak.BleakScanner.discover
.. automethod:: bleak.BleakScanner.find_device_by_name
.. automethod:: bleak.BleakScanner.find_device_by_address
.. automethod:: bleak.BleakScanner.find_device_by_filter
.. autoclass:: bleak.BleakScanner.ExtraArgs
    :members:


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

-------------------------------------------------
Getting discovered devices and advertisement data
-------------------------------------------------

If you aren't using the "easy" class methods, there are three ways to get the
discovered devices and advertisement data.

For event-driven programming, you can provide a ``detection_callback`` callback
to the :class:`BleakScanner` constructor. This will be called back each time
and advertisement is received.

Alternatively, you can utilize the asynchronous iterator to iterate over
advertisements as they are received. The method below returns an async iterator
that yields the same tuples as otherwise provided to ``detection_callback``.

.. automethod:: bleak.BleakScanner.advertisement_data

Otherwise, you can use one of the properties below after scanning has stopped.

.. autoproperty:: bleak.BleakScanner.discovered_devices
.. autoproperty:: bleak.BleakScanner.discovered_devices_and_advertisement_data

----------
Deprecated
----------

.. automethod:: bleak.BleakScanner.register_detection_callback
.. automethod:: bleak.BleakScanner.set_scanning_filter
.. automethod:: bleak.BleakScanner.get_discovered_devices
