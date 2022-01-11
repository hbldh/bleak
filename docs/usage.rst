=====
Usage
=====

.. note::

    A Bluetooth peripheral may have several characteristics with the same UUID, so
    the means of specifying characteristics by UUID or string representation of it
    might not always work in bleak version > 0.7.0. One can now also use the characteristic's
    handle or even the ``BleakGATTCharacteristic`` object itself in
    ``read_gatt_char``, ``write_gatt_char``, ``start_notify``, and ``stop_notify``.


One can use the ``BleakClient`` to connect to a Bluetooth device and read its model number
via the asyncronous context manager like this:

.. code-block:: python

    import asyncio
    from bleak import BleakClient

    address = "24:71:89:cc:09:05"
    MODEL_NBR_UUID = "00002a24-0000-1000-8000-00805f9b34fb"

    async def main(address):
        async with BleakClient(address) as client:
            model_number = await client.read_gatt_char(MODEL_NBR_UUID)
            print("Model Number: {0}".format("".join(map(chr, model_number))))

    asyncio.run(main(address))

or one can do it without the context manager like this:

.. code-block:: python

    import asyncio
    from bleak import BleakClient

    address = "24:71:89:cc:09:05"
    MODEL_NBR_UUID = "00002a24-0000-1000-8000-00805f9b34fb"

    async def main(address):
        client = BleakClient(address)
        try:
            await client.connect()
            model_number = await client.read_gatt_char(MODEL_NBR_UUID)
            print("Model Number: {0}".format("".join(map(chr, model_number))))
        except Exception as e:
            print(e)
        finally:
            await client.disconnect()

    asyncio.run(main(address))

.. warning:: Do not name your script `bleak.py`! It will cause a circular import error.

Make sure you always get to call the disconnect method for a client before discarding it;
the Bluetooth stack on the OS might need to be cleared of residual data which is cached in the
``BleakClient``.

See `examples <https://github.com/hbldh/bleak/tree/master/examples>`_ folder for more code, e.g. on how
to keep a connection alive over a longer duration of time.
