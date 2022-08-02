Windows backend
===============

The Windows backend of bleak is written using the `Bleak WinRT <https://github.com/dlech/bleak-winrt>`_
package to provide bindings for the Windows Runtime (WinRT).

The Windows backend implements a ``BleakClient`` in the module ``bleak.backends.winrt.client``, a ``BleakScanner``
method in the ``bleak.backends.winrt.scanner`` module. There are also backend-specific implementations of the
``BleakGATTService``, ``BleakGATTCharacteristic`` and ``BleakGATTDescriptor`` classes.

Specific features for the Windows backend
-----------------------------------------

Client
~~~~~~
 - The constructor keyword ``address_type`` which can have the values ``"public"`` or ``"random"``. This value
   makes sure that the connection is made in a fashion that suits the peripheral.

Windows backend implementation classes
--------------------------------------

BleakScanner Windows implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.winrt.scanner
    :members:

BLEDevice Windows implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.winrt.device
    :members:

BleakClient Windows implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.winrt.client
    :members:

BleakGATTService Windows implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.winrt.service
    :members:

BleakGATTCharacteristic Windows implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.winrt.characteristic
    :members:


BleakGATTDescriptor Windows implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: bleak.backends.winrt.descriptor
    :members:
