.. _connecting:

**********
Connecting
**********

One can use the :class:`<BleakClient> bleak.backends.client.BleakClient` to connect to a Bluetooth device and read its model number
via the asynchronous context manager like this:

.. code-block:: python

    import asyncio
    from bleak import BleakClient, BleakScanner

    address = "24:71:89:cc:09:05"
    MODEL_NBR_UUID = "00002a24-0000-1000-8000-00805f9b34fb"

    async def run(address):
        device = await BleakScanner.find_device_by_address(address)
        async with BleakClient(device) as client:
            model_number = await client.read_gatt_char(MODEL_NBR_UUID)
            print("Model Number: {0}".format("".join(map(chr, model_number))))

    asyncio.run(run(address))

or one can do it without the context manager like this:

.. code-block:: python

    import asyncio
    from bleak import BleakClient, BleakScanner

    address = "24:71:89:cc:09:05"
    MODEL_NBR_UUID = "00002a24-0000-1000-8000-00805f9b34fb"

    async def run(address):
        device = await BleakScanner.find_device_by_address(address)
        client = BleakClient(device)
        try:
            await client.connect()
            model_number = await client.read_gatt_char(MODEL_NBR_UUID)
            print("Model Number: {0}".format("".join(map(chr, model_number))))
        except Exception as e:
            print(e)
        finally:
            await client.disconnect()

    asyncio.run(run(address))

Make sure you always get to call the disconnect method for a client before discarding it;
the Bluetooth stack on the OS might need to be cleared of residual data which is cached in the
:class:`<BleakClient> bleak.backends.client.BleakClient`.

.. note::

    It is possible to send the address string directly to the :class:`<BleakClient> bleak.backends.client.BleakClient`
    constructor or context manager, in which case a `await BleakScanner.find_device_by_address(address)` is done
    inside the ``connect`` call. However, it is recommended to do them separately like this to get a better
    opportunity to handle situations where Bleak did not detect the device.
