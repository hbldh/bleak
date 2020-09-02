macOS backend
=============

The macOS backend of Bleak is written with
`pyobjc <https://pyobjc.readthedocs.io/en/latest/>`_ directives for interfacing
with `Foundation <https://pyobjc.readthedocs.io/en/latest/apinotes/Foundation.html>`_
and `CoreBluetooth <https://pyobjc.readthedocs.io/en/latest/apinotes/CoreBluetooth.html>`_ APIs.

Specific features for the macOS backend
---------------------------------------

The most noticeable difference between the other
backends of bleak and this backend, is that CoreBluetooth doesn't scan for
other devices via Bluetooth address. Instead, UUIDs are utilized that are often
unique between the device that is scanning and the device that is being scanned.

In the example files, this is handled in this fashion:

.. code-block:: python

    mac_addr = (
        "24:71:89:cc:09:05"
        if platform.system() != "Darwin"
        else "243E23AE-4A99-406C-B317-18F1BD7B4CBE"
    )

As stated above, this will however only work the macOS machine that performed
the scan and thus cached the device as ``243E23AE-4A99-406C-B317-18F1BD7B4CBE``.

There is also no pairing functionality implemented in macOS right now, since it does not seem
to be any explicit pairing methods in the COre Bluetooth.
