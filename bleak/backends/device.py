# -*- coding: utf-8 -*-
"""
Wrapper class for Bluetooth LE servers returned from calling
:py:meth:`bleak.discover`.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""


class BLEDevice:
    """A simple wrapper class representing a BLE server detected during
    a `discover` call.

    - When using Windows backend, `details` attribute is a
      ``Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisement`` object, unless
      it is created with the Windows.Devices.Enumeration discovery method, then is is a
      ``Windows.Devices.Enumeration.DeviceInformation``.
    - When using Linux backend, ``details`` attribute is a
      dict with keys ``path`` which has the string path to the DBus device object and ``props``
      which houses the properties dictionary of the D-Bus Device.
    - When using macOS backend, ``details`` attribute will be a CBPeripheral object.
    """

    def __init__(self, address, name=None, details=None, rssi=0, **kwargs):
        #: The Bluetooth address of the device on this machine.
        self.address = address
        #: The advertised name of the device.
        self.name = name
        #: The OS native details required for connecting to the device.
        self.details = details
        #: RSSI, if available
        self.rssi = rssi
        #: Device specific details. Contains a ``uuids`` key which is a list of service UUIDs and a ``manufacturer_data`` field with a bytes-object from the advertised data.
        self.metadata = kwargs

    def __str__(self):
        return f"{self.address}: {self.name}"

    def __repr__(self):
        return f"BLEDevice({self.address}, {self.name})"
