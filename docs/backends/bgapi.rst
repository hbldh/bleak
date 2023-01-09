.. _bgapi-backend:

Silicon Labs BGAPI backend
=============

The BGAPI backend of Bleak communicates with any device that implements Silicon Labs "BGAPI"
Protocol.  Classically, this is a Silicon Labs microcontroller, attached via a serial port,
which has been programmed with some variant of "NCP" (Network Co-Processor) firmware.

This does `not` apply to devices using "RCP" (Radio Co-Processor) firmware, as those only
expose the much lower level HCI interface.

References:
 * `AN1259: Using the v3.x Silicon Labs Bluetooth Stack in Network Co-Processor Mode <https://www.silabs.com/documents/public/application-notes/an1259-bt-ncp-mode-sdk-v3x.pdf>`_
 * https://docs.silabs.com/bluetooth/5.0/index

Requirements
------
This backend uses `pyBGAPI <https://pypi.org/project/pybgapi/>`_ to handle the protocol layers.


Usage
-----
This backend can either be explicitly selected via the ``backend`` kwarg when creating a BleakClient,
or, environment variables can be used.

Environment variables understood:
 * BLEAK_BGAPI_XAPI Must be a path to the ``sl_bt.xapi`` file.
   If this env var exists, the BGAPI backend will be automatically loaded
 * BLEAK_BGAPI_ADAPTER The serial port to use, eg ``/dev/ttyACM1``
 * BLEAK_BGAPI_BAUDRATE The serial baudrate to use when opening the port, if required.

Alternatively, these can all be provided directly as kwargs, as show below:

.. code-block:: python

    async with bleak.BleakClient(
            "11:aa:bb:cc:22:33",
            backend=bleak.backends.bgapi.client.BleakClientBGAPI,
            bgapi="/home/.../SimplicityStudio/SDKs/gecko-4.2.0/protocol/bluetooth/api/sl_bt.xapi",
            adapter="/dev/ttyACM1",
            baudrate=921600,
            ) as client:
        logging.info("Connected to %s", client)

Pay attention that the ``bgapi`` file must be provided, corresponding to the firmware used on your device.
These files can be found in the `Silicon Labs Gecko SDK <https://github.com/SiliconLabs/gecko_sdk/>`_ in
the ``protocol/bluetooth/api`` directory.

Likewise, the ``adapter`` kwarg should be used to specify where the device is attached.

At the time of writing, support for sockets or the Silicon Labs CPC daemon is not tested.



API
---

Scanner
~~~~~~~

.. automodule:: bleak.backends.bluezdbus.scanner
    :members:

Client
~~~~~~

.. automodule:: bleak.backends.bluezdbus.client
    :members:

.. _`asyncio event loop`: https://docs.python.org/3/library/asyncio-eventloop.html
