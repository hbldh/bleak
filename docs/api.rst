API
===

The naming of things can be confusing when using Bluetooth LE, due to the many possible meanings of
words like "device" or "service" depending on the context. Here is a quick breakdown of the main object
types used in bleak and their meaning, roughly in the order in which you will often use them in your code:

* :py:class:`bleak.BleakScanner` finds advertising BLE devices (also known as servers)
* :py:class:`bleak.BLEDevice` the representation (think: name or address) of such a BLE device
* :py:class:`bleak.BleakClient` an open connection to a BLE device
* :py:class:`bleak.BleakGATTServiceCollection` the collection of services implemented in a BLE device
* :py:class:`bleak.BleakGATTService` the name (or address) of a service implemented in a BLE device
* :py:class:`bleak.BleakGATTCharacteristic` the name (or address) of a charactieristic (think: attribute or variable) implemented by such a service
* :py:class:`bleak.BleakGATTDescriptor` extra properties of a charactieristic (think: user-readable name, or binary format)

You can then read and write characteristic values by calling methods of :py:class:`bleak.BleakClient`,
passing the :py:class:`bleak.backends.service.BleakGATTCharacteristic` of the value you are interested in.

In this documentation and in other literature on Bluetooth LE GATT you will also come across the terms _attribute_ and _handle_.
You probably need not bother with attribute (it is the "superclass" of the other GATT types). A handle is the low-level
way to address services, characteristics, descriptors and values. Using handles is supported by various bleak APIs, and while
it can sometimes be useful, for example to communicate with devices that have characteristics with non-unique UUIDs and you do 
not have the :py:class:`bleak.BleakGATTCharacteristic`, or when you need to do
things that are uncommon, such as writing to a descriptor.

Scanning
--------

Use the top-level :py:class:`bleak.BleakScanner` object to scan for BLE 
devices. The constructor may have 
additional platform-specific arguments which you can find in the relevant 
:doc:`apiimplementations` section. You can limit the scan to only look for a device with a specific name,
or only for devices that implement a specific service.

The scanner will return :py:class:`bleak.BLEDevice` objects.

Scanner interface
~~~~~~~~~~~~~~~~~

.. autoclass:: bleak.BleakScanner
    :members:
    :inherited-members:

.. autoclass:: bleak.BLEDevice
    :members:
    :inherited-members:

.. autoclass:: bleak.AdvertisementData
    :members:
    :inherited-members:

.. autoclass:: bleak.AdvertisementDataCallback
    :members:
    :inherited-members:

.. autoclass:: bleak.AdvertisementDataFilter
    :members:
    :inherited-members:

Connecting
----------

After you find the correct :py:class:`bleak.BLEDevice` you will use the top-level :py:class:`bleak.BleakClient` object to connect to a BLE 
device and communicate with it. Alternatively, you can pass the BLE address of the device you want to connect to, and an automatic scan
operation is performed.

Some of the methods, especially the constructor, may have 
additional platform-specific arguments which you can find in the relevant 
:doc:`apiimplementations` section.


Client interface
~~~~~~~~~~~~~~~~

.. autoclass:: bleak.BleakClient
    :members:
    :inherited-members:

Enumerating
-----------

Once you have an open :py:class:`bleak.BleakClient` connection you can read 
from the BLE device (or write values, or be notified by the device when a value
changes), but you have to know how to specify the right item.

For this there is a set of classes that allow you to enumerate over the services 
and characteristics supported by the BLE device, how you can access them 
(read, write, notify), what they mean (human readable description) and what type
of values they are (int, string, etc):

.. autoclass:: bleak.BleakGATTServiceCollection
    :members:
    :inherited-members:

.. autoclass:: bleak.BleakGATTService
    :members:
    :inherited-members:

.. autoclass:: bleak.BleakGATTCharacteristic
    :members:
    :inherited-members:

.. autoclass:: bleak.BleakGATTDescriptor
    :members:
    :inherited-members:

Exceptions
----------

.. automodule:: bleak.exc
    :members:

Utilities
---------

.. automodule:: bleak.uuids
    :members:
