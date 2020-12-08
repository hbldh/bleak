Windows backend
===============

The Windows backend of bleak is written using the `Python for .NET <https://pythonnet.github.io/>`_
package. Combined with a thin bridge library (`BleakUWPBridge <https://github.com/hbldh/BleakUWPBridge>`_)
that is bundled with bleak, the .NET Bluetooth components can be used from Python.

The Windows backend implements a ``BleakClient`` in the module ``bleak.backends.dotnet.client``, a ``BleakScanner``
method in the ``bleak.backends.dotnet.scanner`` module. There are also backend-specific implementations of the
``BleakGATTService``, ``BleakGATTCharacteristic`` and ``BleakGATTDescriptor`` classes.

Finally, some .NET/``asyncio``-connectivity methods are available in the ``bleak.backends.dotnet.utils`` module.

Specific features for the Windows backend
-----------------------------------------

Client
~~~~~~
 - The constructor keyword ``address_type`` which can have the values ``"public"`` or ``"random"``. This value
   makes sure that the connection is made in a fashion that suits the peripheral.

