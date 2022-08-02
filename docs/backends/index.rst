Bleak backends
==============

Bleak hides most of the details of the Bluetooth LE stack provided by the operating system, and
you should normally use the APIs as specified in the :ref:`api` section,
but sometimes it may be useful to access those details because it provides useful functionality.

But note that by using features described here your code may no longer be portable to other operating systems,
and moreover the backend APIs should not be considered stable, and can change between releases.

Bleak supports the following operating systems:

* Windows 10, version 16299 (Fall Creators Update) and greater
* Linux distributions with BlueZ >= 5.43 (See :ref:`linux-backend` for more details)
* OS X/macOS support via Core Bluetooth API, from at least version 10.11
* Partial Android support mostly using Python-for-Android/Kivy.

These pages document platform specific differences from the interface API.

There is an additional subsection with information on creating new backend implementations.

Contents:

.. toctree::
   :maxdepth: 2

   windows
   linux
   macos
   android
   baseclasses
