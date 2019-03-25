=====
Usage
=====

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


Connect to a Bluetooth device and read it's model number:

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


See `examples <https://github.com/hbldh/bleak/tree/master/examples>`_ folder for more code.
