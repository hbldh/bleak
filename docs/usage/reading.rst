************
Reading Data
************

Reading data from characteristics has already been included in the examples on :ref:`connecting`,
but there are some finer points to it that will be dealt with here as well.


Reading from characteristics
----------------------------

A :py:class:`bleak.backends.characteristic.BleakGATTCharacteristic` wraps the OS native representation
of the connected peripheral's GATT Characteristic. To read from a characteristic in Bleak, you can
provide either the UUID for that characteristic,
the integer ID called a handle that the peripheral has assigned to its characteristics,
or by sending in the :py:class:`bleak.backends.characteristic.BleakGATTCharacteristic`
instance itself:

.. code-block:: python

    import asyncio
    from bleak import BleakClient, BleakScanner
    from bleak.uuids import uuidstr_to_str

    address = "24:71:89:cc:09:05"

    async def run(address):
        device = await BleakScanner.find_device_by_address(address)
        async with BleakClient(device) as client:
            services = await client.get_services()
            # Find the service with the name Device Information
            device_information_service = [
                s
                for s in services.services.values()
                if s.description == "Device Information"
            ][0]
            for char in device_information_service.characteristics:
                if uuidstr_to_str(char.uuid) == "Model Number String":
                    # Found the characteristic we were looking for.
                    # Now we read from it using all three possible ways.
                    model_number_1 = await client.read_gatt_char(char)
                    print(
                        f"Model Number using {char} (Type: {type(char)}): {model_number_1.decode()}"
                    )
                    model_number_2 = await client.read_gatt_char(char.uuid)
                    print(
                        f"Model Number using {char.uuid} (Type: {type(char.uuid)}): {model_number_2.decode()}"
                    )
                    model_number_3 = await client.read_gatt_char(char.handle)
                    print(
                        f"Model Number using {char.handle} (Type: {type(char.handle)}): {model_number_3.decode()}"
                    )
                    break

    asyncio.run(run(address))

The output from running this script is then something like

.. code-block::bash

    Model Number using 00002a24-0000-1000-8000-00805f9b34fb (Handle: 12):  (Type: <class 'bleak.backends.winrt.characteristic.BleakGATTCharacteristicWinRT'>): CC2650 SensorTag
    Model Number using 00002a24-0000-1000-8000-00805f9b34fb (Type: <class 'str'>): CC2650 SensorTag
    Model Number using 12 (Type: <class 'int'>): CC2650 SensorTag

This is a very cumbersome way of finding characteristics and reading from characteristics, but it makes
no assumptions except knowing what the BLE names of those characteristics are. It is a better
idea to run the `Service Explorer example <https://github.com/hbldh/bleak/blob/master/examples/service_explorer.py>`_
when you start working with a new peripheral, in order to get a complete map of all available endpoints in the
peripheral and their corresponding UUID and handle.

There is a possibility of having several characteristics with the same UUID on a peripheral, but they
always have a unique handle. Trying to read from a characteristic by providing the uuid while there
are multiple characteristics available will result in Bleak throwing a
:py:exc:`bleak.exc.BleakError`.

Cached Values
^^^^^^^^^^^^^

When you call :py:meth:`bleak.backends.client.read_gatt_char`, Bleak will by default ask the
peripheral to send the value. In some cases the values are static and wil not change. In that case
one can send the `use_cached=True` keyword in the :py:meth:`bleak.backends.client.read_gatt_char`
call to use the value cached in the OS, to avoid the round trip to the actual device. This might result
in faster execution times when reading.
