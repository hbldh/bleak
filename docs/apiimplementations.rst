API Implementations
===================

Bleak hides most of the details of the Bluetooth LE stack provided by the operating system,
but sometimes it may be useful to access those details because it provides useful functionality.

But note that by using features described here your code may no longer be portable to other operating systems,
 and moreover the backend APIs should not be considered stable, and can change between releases.

Windows
-------

BleakClient Windows implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.winrt.client
    :members:

BleakScanner Windows implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.winrt.scanner
    :members:

MacOS
-----

BleakClient MacOS implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.corebluetooth.client
    :members:

BleakScanner MacOS implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.corebluetooth.scanner
    :members:

Linux
-----

BleakClient Linux Distributions with BlueZ implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.bluezdbus.client
    :members:

BleakScanner Linux Distributions with BlueZ implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.bluezdbus.scanner
    :members:

Android
-------

BleakClient Python-for-Android/Kivy implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.p4android.client
    :members:

BleakScanner Python-for-Android/Kivy implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.p4android.scanner
    :members:

Backend base classes
--------------------

The backend base classes are usually not used directly, they documented mainly for convenience
of people writing a new backend.

.. automodule:: bleak.backends.scanner
    :members:

.. automodule:: bleak.backends.client
    :members:
