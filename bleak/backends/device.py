# -*- coding: utf-8 -*-
"""
Wrapper class for Bluetooth LE servers returned from calling
:py:meth:`bleak.discover`.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""
from ._manufacturers import MANUFACTURERS


class BLEDevice(object):
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

    def __init__(self, address, name, details=None, rssi=0, **kwargs):
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
        if not self.name:
            if "manufacturer_data" in self.metadata:
                ks = list(self.metadata["manufacturer_data"].keys())
                if len(ks):
                    mf = MANUFACTURERS.get(ks[0], MANUFACTURERS.get(0xFFFF))
                    value = self.metadata["manufacturer_data"].get(
                        ks[0], MANUFACTURERS.get(0xFFFF)
                    )
                    # TODO: Evaluate how to interpret the value of the company identifier...
                    return "{0}: {1} ({2})".format(self.address, mf, value)
        return "{0}: {1}".format(self.address, self.name or "Unknown")

    def __repr__(self):
        return str(self)
