==================
BleakAdapter class
==================

.. py:currentmodule:: bleak

.. autoclass:: bleak.BleakAdapter

------------------------
Getting an adapter
------------------------

A :class:`BleakAdapter` instance is created via the async
:meth:`BleakAdapter.get` factory method::

    import asyncio
    from bleak import BleakAdapter

    async def main():
        adapter = await BleakAdapter.get()
        ...

    asyncio.run(main())

On Linux, a specific adapter can be selected via the ``bluez`` argument::

    adapter = await BleakAdapter.get(bluez={"adapter": "hci1"})

.. automethod:: bleak.BleakAdapter.get

-----------------------------
Listing connected BLE devices
-----------------------------

The adapter can be queried for BLE devices that are already connected to the
system. The returned :class:`BLEDevice` objects can be passed directly to
:class:`BleakClient` to use the existing OS-level connection without scanning::

    from bleak import BleakAdapter, BleakClient

    adapter = await BleakAdapter.get()
    devices = await adapter.get_connected_devices()

    for d in devices:
        print(d.name, d.address)

    # Use an existing connection without scanning
    async with BleakClient(devices[0]) as client:
        ...

.. automethod:: bleak.BleakAdapter.get_connected_devices
