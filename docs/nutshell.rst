.. _nutshell:

What Bleak is and what it isn't
===============================

The state of Bluetooth Low Energy in Python when I started to implement Bleak was such that there was no package that could run in Windows, macOS and
Linux-distributions, at least not without installing a lot of non-pip software and compilers to be able to install it.
I found that discouraging and wanted to see if something could be done about that.

I wanted to implement a Bluetooth Low Energy Central/Client API which fulfilled the following criteria:

1. Bleak should be possible to use on Windows, macOS and Linux-distributions
2. Bleak should have a identical API with as few as possible of functional differences between OS implementations
3. Bleak should be pip-installable with no install-time compilations
4. Bleak should use only OS native BLE components, preferably ones installed as default in the OS so no extra non-pip installations are necessary
5. Bleak should use the ``asyncio`` standard library and its event loops, at least where the Bleak user is concerned

This package is the results. It is not the best Python BLE package when it comes to number of features or speed of notification handling,
but it does provide an immediate way to start experimenting with BLE devices using Python on all major operating systems.

These Bluetooth Low Energy features are implemented in Bleak:

- Scan for devices
- Connect to device
- Pair with device (as of Bleak 0.8.0, in Windows and Linux)
- Getting GATT Services
- Read from GATT Characteristics
- Write to GATT Characteristics
- Receive Notifications/Indications from GATT Characteristics
- Read from GATT Descriptors
- Write to GATT Descriptors

If you have need of a BLE feature that is not present in the list above, then Bleak is not what you are looking for.

If you are looking for implementing a GATT server / BLE peripheral of your own, then the companion package
`Bless <https://github.com/kevincar/bless>`_ is what you are looking.
