Backend implementations
=======================

Bleak supports the following operating systems:

* Windows 10, version 16299 (Fall Creators Update) and greater
* Linux distributions with BlueZ >= 5.43 (See :ref:`linux-backend` for more details)
* OS X/macOS support via Core Bluetooth API, from at least version 10.11
* Partial Android support mostly using Python-for-Android/Kivy.

These pages document platform specific differences from the interface API.

Contents:

.. toctree::
   :maxdepth: 2

   windows
   linux
   macos
   android

Shared Backend API
------------------

.. warning:: The backend APIs are not considered part of the stable API and
    may change without notice.

Scanner
~~~~~~~

.. automodule:: bleak.backends.scanner
    :members:

Client
~~~~~~

.. automodule:: bleak.backends.client
    :members:
