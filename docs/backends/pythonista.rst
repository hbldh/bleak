Pythonista iOS app backend
==========================

Pythonista iOS app backend of Bleak is written as 3rd-party module `bleak-pythonista <https://pypi.org/project/bleak-pythonista/>`_ with
`pythonista built-in _cb module (CoreBluetooth wrapper) <https://omz-software.com/pythonista/docs/ios/cb.html/>`_ directives for interfacing

* This backend refers to `Pythonista.cb docs <https://omz-software.com/pythonista/docs/ios/cb.html>`_
* This backend refers to existing `macOS CoreBluetooth bleak backend <https://github.com/hbldh/bleak/tree/develop/bleak/backends/corebluetooth>`_ was used as a reference
* It also provides stub files for pythonista built-in modules as ``_cb`` and ``pythonista.cb``, and fake ``_cb.py`` implementation for testing on unsupported platforms
* Use `Bleak docs <https://github.com/hbldh/bleak/blob/develop/README.rst>`_ to explore how to use Bleak

.. note:: bleak-pythonista sources aren't included with Bleak. Explore them here: `bleak-pythonista on GitHub <https://github.com/o-murphy/bleak-pythonista>`_


Optional installation with Bleak
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use `StaSh <https://github.com/ywangd/stash>`_
or `Pythonista3_pip_Configration_Tool <https://github.com/CrossDarkrix/Pythonista3_pip_Configration_Tool>`_ for pip

.. code-block:: console

    $ pip install bleak[pythonista]


Specific features for the Pythonista iOS app backend
----------------------------------------------------

The most noticeable difference between the other
backends of bleak and this backend, is that pythonista ``_cb`` (CoreBluetooth wrapper) doesn't scan for
other devices via Bluetooth address. Instead, UUIDs are utilized that are often
unique between the device that is scanning and the device that is being scanned.

In the example files, this is handled in this fashion:

.. code-block:: python

    mac_addr = (
        "24:71:89:cc:09:05"
        if sys.platform != "darwin"
        else "243E23AE-4A99-406C-B317-18F1BD7B4CBE"
    )

As stated above, this will however only work the Apple device that performed
the scan and thus cached the device as ``243E23AE-4A99-406C-B317-18F1BD7B4CBE``.

Pairing
^^^^^^^
There is no pairing functionality implemented in Pythonista iOS app right now, since it does not seem
to be any explicit pairing methods in Pythonista ``_cb`` (CoreBluetooth wrapper).

Instead, iOS will prompt the user the first time a characteristic that requires
authorization/authentication is accessed. This means that a GATT read or write
operation could block for a long time waiting for the user to response. So
timeouts should be set accordingly.

Calling the :meth:`bleak.BleakClient.pair` method will raise a ``NotImplementedError``
on iOS. But setting ``pair=True`` in :class:`bleak.BleakClient` will be silently ignored.

Characteristic descriptors
^^^^^^^^^^^^^^^^^^^^^^^^^^
There is no functionality to get characteristic descriptors implemented in Pythonista iOS app right now.

Calling the :meth:`bleak.BleakClient.read_gatt_descriptor` method will raise a ``NotImplementedError``
on Pythonista iOS app.
Calling the :meth:`bleak.BleakClient.write_gatt_descriptor` method will raise a ``NotImplementedError``
on Pythonista iOS app.

Notifications
^^^^^^^^^^^^^
Pythonista ``_cb`` (CoreBluetooth wrapper) does not differentiate between data from a notification and data from a read.
This can cause confusion in cases where a device may send a notification message on a characteristic
as a signal that the characteristic needs to be read again.

Bleak can accept a ``notification_discriminator`` callback in the ``cb`` dict parameter that is
passed to the :meth:`bleak.BleakClient.start_notify` method that can differentiate between these types of data.

.. code-block:: python

    event = asyncio.Event()

    async def notification_handler(char, data):
        event.set()

    def notification_check_handler(data):
        # We can identify notifications on this characteristic because they
        # only contain 1 byte of data. Read responses will have more than
        # 1 byte.
        return len(data) == 1

    await client.start_notify(
        char,
        notification_handler,
        cb={"notification_discriminator": notification_check_handler},
    )

    while True:
        await event.wait()
        # We received a notification - prepare to receive another
        event.clear()
        # Then read the characteristic to get the full value
        data = await client.read_gatt_char(char)
        # Do stuff with data
