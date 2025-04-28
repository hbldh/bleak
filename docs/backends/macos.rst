macOS backend
=============

The macOS backend of Bleak is written with
`pyobjc <https://pyobjc.readthedocs.io/en/latest/>`_ directives for interfacing
with `Foundation <https://pyobjc.readthedocs.io/en/latest/apinotes/Foundation.html>`_
and `CoreBluetooth <https://pyobjc.readthedocs.io/en/latest/apinotes/CoreBluetooth.html>`_ APIs.

Specific features for the macOS backend
---------------------------------------

The most noticeable difference between the other
backends of bleak and this backend, is that CoreBluetooth doesn't scan for
other devices via Bluetooth address. Instead, UUIDs are utilized that are often
unique between the device that is scanning and the device that is being scanned.

In the example files, this is handled in this fashion:

.. code-block:: python

    mac_addr = (
        "24:71:89:cc:09:05"
        if platform.system() != "Darwin"
        else "243E23AE-4A99-406C-B317-18F1BD7B4CBE"
    )

As stated above, this will however only work the macOS machine that performed
the scan and thus cached the device as ``243E23AE-4A99-406C-B317-18F1BD7B4CBE``.

There is also no pairing functionality implemented in macOS right now, since it does not seem
to be any explicit pairing methods in the Core Bluetooth.

CoreBluetooth does not differentiate between data from a notification, and data from a read.
This can cause confusion in cases where a device may send a notification message on a characteristic
that is an indication that the characteristic needs to be read again.

Bleak has can accept a ``notification_discriminator`` callback in the ``cb`` dict parameter that is
passed to the start_notify function that can differentiate between these types of data.

.. code-block:: python

    async def reread(char):
        data = await client.read_gatt_char(char)

    async def notification_handler(char, data):
        asyncio.create_task(reread(char))

    def notification_check_handler(data):
        return len(data) == 1

    await client.start_notify(
        CHARACTERISTIC_UUID,
        notification_handler,
        cb=dict(notification_discriminator=notification_check_handler),
    )

API
---

Scanner
~~~~~~~

.. automodule:: bleak.backends.corebluetooth.scanner
    :members:

Client
~~~~~~

.. automodule:: bleak.backends.corebluetooth.client
    :members:
