Bumble backend
===============

This backend adds support for the |bumble| Bluetooth Controller Stack from Google.
The backend enables support of multiple |bumble_transport| to communicate with
a physical or virtual HCI controller.

Use cases for this backend are:

1. Use of an HCI Controller (e.g. serial/USB) that is not supported natively by an OS.
2. Bluetooth Functional tests without Hardware. Example of Bluetooth stacks that
   support virtualization are |android_emulator| and |zephyr|.
3. Connection of HCI Controllers that are not in the same radio network (virtual or physical).


Installation
------------

To install the Bumble backend, you need to install the ``bleak`` package with the
``bumble`` optional dependency.

.. code-block:: bash

    pip install bleak[bumble]


Usage
------------

To enable the backend you need to set the environmental variable ``BLEAK_BUMBLE``. The expected
value is the transport plus specific arguments as specified from the |bumble_transport|.
For example to use the TCP Server at localhost port 1000 you can set ``BLEAK_BUMBLE=tcp-server:_:1000``.
This option allows to change between the native OS backend and the Bumble backend without changing the code.

Optionally if you want to use the backend without the environmental variable, you can define
the backend directly with the argument ``backend``.
To select the specific transport you can use the ``cfg`` argument when declaring the backend.

.. code-block:: python

    from bleak import BleakScanner, BleakClient
    from bleak.backends.bumble import BumbleTransportCfg, TransportScheme
    from bleak.backends.bumble.scanner import BleakScannerBumble
    from bleak.backends.bumble.client import BleakClientBumble

    cfg = BumbleTransportCfg(TransportScheme.TCP_SERVER, "127.0.0.1:1000")
    scanner = BleakScanner(backend=BleakScannerBumble, cfg=cfg)
    async for bd, ad in scanner.advertisement_data():
        client = BleakClient(backend = BleakClientBumble, cfg=cfg)
        await client.connect()

HCI Mode
~~~~~~~~~~~~

Bumble can be used either as a Bluetooth HCI Controller or HCI Host. By default, it is used
as an HCI Controller. If however you want to use it as an HCI Host you can set the
the environmental variable ``BLEAK_BUMBLE_HOST``. Host mode is typically used when your
application will be running on a device that has a Bluetooth Controller (e.g. USB, serial).

Optionally you can set the host mode directly in the backend declaration with the argument ``host_mode``.

.. code-block:: python

    from bleak import BleakScanner, BleakClient
    from bleak.backends.bumble import BumbleTransportCfg, TransportScheme
    from bleak.backends.bumble.scanner import BleakScannerBumble
    from bleak.backends.bumble.client import BleakClientBumble

    cfg = BumbleTransportCfg(TransportScheme.TCP_SERVER, "127.0.0.1:1000")
    scanner = BleakScanner(backend=BleakScannerBumble, cfg=cfg, host_mode=True)
    async for bd, ad in scanner.advertisement_data():
        client = BleakClient(backend = BleakClientBumble, cfg=cfg, host_mode=True)
        await client.connect()


Examples
---------

Zephyr RTOS
~~~~~~~~~~~~

Zephyr RTOS supports a |zephyr_virtual| over a TCP client. To connect your application with zephyr
you need to define a |tcp_server| transport for bumble.

.. code-block:: python

    from bleak.backends.bumble import BumbleTransport, TransportScheme
    from bleak import BleakScanner, BleakClient
    from bleak.backends.bumble.scanner import BleakScannerBumble
    from bleak.backends.bumble.client import BleakClientBumble

    transport = BumbleTransport(TransportScheme.TCP_SERVER,"127.0.0.1:1000")
    scanner = BleakScanner(backend=BleakScannerBumble, adapter=transport)
    async for bd, ad in scanner.advertisement_data():
        client = BleakClient(bd,backend=BleakClientBumble)
        await client.connect()

In the previous code snippet the bumble backend will create a TCP server on the localhost
at port 1000.

.. note::

    The Zephyr application must be compiled for the ``native/posix/64`` board. The Bumble
    controller does not support all HCI LE Commands. For this reason the following configs
    must be disabled in the Zephyr firmware: ``CONFIG_BT_EXT_ADV``, ``CONFIG_BT_AUTO_PHY_UPDATE``,
    ``CONFIG_BT_HCI_ACL_FLOW_CONTROL``.


Android Emulator
~~~~~~~~~~~~~~~~

The  |android_emulator| supports virtualization of the Bluetooth Controller
over gRPC with the android |netsim| tool.

.. code-block:: python

    from bleak.backends.bumble import BumbleTransport, TransportScheme
    from bleak import BleakScanner, BleakClient
    from bleak.backends.bumble.scanner import BleakScannerBumble
    from bleak.backends.bumble.client import BleakClientBumble

    transport = BumbleTransport(TransportScheme.ANDROID_NETSIM)
    scanner = BleakScanner(backend=BleakScannerBumble, adapter=transport)
    async for bd, ad in scanner.advertisement_data():
        client = BleakClient(bd,backend=BleakClientBumble)
        await client.connect()


API
---

Transport
~~~~~~~~~

.. autoclass:: bleak.backends.bumble::TransportScheme
    :members:
.. autoclass:: bleak.backends.bumble::BumbleTransport

Scanner
~~~~~~~

.. automodule:: bleak.backends.bumble.scanner
    :members:


Client
~~~~~~

.. automodule:: bleak.backends.bumble.client
    :members:


.. |bumble| raw:: html

   <a href="https://github.com/google/bumble" target="_blank">Bumble</a>

.. |bumble_transport| raw:: html

   <a href="https://google.github.io/bumble/transports/index.html" target="_blank">bumble transports</a>

.. |android_emulator| raw:: html

   <a href="https://developer.android.com/studio/run/emulator" target="_blank">Android Emulator</a>

.. |zephyr| raw:: html

   <a href="https://github.com/zephyrproject-rtos/zephyr" target="_blank">Zephyr RTOS</a>

.. |zephyr_virtual| raw:: html

   <a href="https://docs.zephyrproject.org/3.7.0/connectivity/bluetooth/bluetooth-tools.html#running-on-a-virtual-controller-and-native-sim" target="_blank">Virtual HCI</a>

.. |tcp_server| raw:: html

   <a href="https://google.github.io/bumble/transports/tcp_server.html" target="_blank">TCP Server</a>

.. |netsim| raw:: html

   <a href="https://android.googlesource.com/platform/tools/netsim/" target="_blank">netsim</a>
