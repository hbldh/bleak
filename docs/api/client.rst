=================
BleakClient class
=================

.. autoclass:: bleak.BleakClient

----------------------------
Connecting and disconnecting
----------------------------

Before doing anything else with a :class:`BleakClient` object, it must be connected.

:class:`bleak.BleakClient` is a an async context manager, so the recommended
way of connecting is to use it as such::

    import asyncio
    from bleak import BleakClient

    async def main():
        async with BleakClient("XX:XX:XX:XX:XX:XX") as client:
            # Read a characteristic, etc.
            ...

        # Device will disconnect when block exits.
        ...

    # Using asyncio.run() is important to ensure that device disconnects on
    # KeyboardInterrupt or other unhandled exception.
    asyncio.run(main())


It is also possible to connect and disconnect without a context manager, however
this can leave the device still connected when the program exits:

.. automethod:: bleak.BleakClient.connect
.. automethod:: bleak.BleakClient.disconnect

The current connection status can be retrieved with:

.. autoproperty:: bleak.BleakClient.is_connected

A callback can be provided to the :class:`BleakClient` constructor via the
``disconnect_callback`` argument to be notified of disconnection events.


------------------
Device information
------------------

.. autoproperty:: bleak.BleakClient.address

.. autoproperty:: bleak.BleakClient.mtu_size


----------------------
GATT Client Operations
----------------------

All Bluetooth Low Energy devices use a common Generic Attribute Profile (GATT)
for interacting with the device after it is connected. Some GATT operations
like discovering the services/characteristic/descriptors and negotiating the
MTU are handled automatically by Bleak and/or the OS Bluetooth stack.

The primary operations for the Bleak client are reading, writing and subscribing
to characteristics.

Services
========

The available services on a device are automatically enumerated when connecting
to a device. Services describe the devices capabilities.

.. autoproperty:: bleak.BleakClient.services


GATT characteristics
====================

Most I/O with a device is done via the characteristics.

.. automethod:: bleak.BleakClient.read_gatt_char
.. automethod:: bleak.BleakClient.write_gatt_char
.. automethod:: bleak.BleakClient.start_notify
.. automethod:: bleak.BleakClient.stop_notify


GATT descriptors
================

Descriptors can provide additional information about a characteristic.

.. automethod:: bleak.BleakClient.read_gatt_descriptor
.. automethod:: bleak.BleakClient.write_gatt_descriptor


---------------
Pairing/bonding
---------------

On some devices, some characteristics may require authentication in order to
read or write the characteristic. In this case pairing/bonding the device is
required.


.. automethod:: bleak.BleakClient.pair
.. automethod:: bleak.BleakClient.unpair


----------
Deprecated
----------

.. automethod:: bleak.BleakClient.set_disconnected_callback
.. automethod:: bleak.BleakClient.get_services
