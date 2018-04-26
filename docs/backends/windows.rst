Windows backend
===============

The Windows backend of bleak is written using the `Python for .NET <https://pythonnet.github.io/>`_
package. Combined with a thin bridge library (`BleakUWPBridge <https://github.com/hbldh/BleakUWPBridge>`_)
that is bundled with bleak, the .NET Bluetooth components can be used from Python.

API
---

Discover
~~~~~~~~

.. automodule:: bleak.backends.dotnet.discovery
    :members:

Client
~~~~~~

.. automodule:: bleak.backends.dotnet.client
    :members:

Utils
~~~~~~

.. automodule:: bleak.backends.dotnet.utils
    :members:
