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
      `Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisement` object.
    - When using Linux backend, `details` attribute is a
      string path to the DBus device object.
    - When using macOS backend, `details` attribute will be
      something else.

    """

    def __init__(self, address, name, details=None, **kwargs):
        self.address = address
        self.name = name if name else "Unknown"
        self.details = details
        self.metadata = kwargs

    def __str__(self):
        if self.name == "Unknown":
            if "manufacturer_data" in self.metadata:
                ks = list(self.metadata["manufacturer_data"].keys())
                if len(ks):
                    mf = MANUFACTURERS.get(ks[0], MANUFACTURERS.get(0xffff))
                    value = self.metadata["manufacturer_data"].get(
                        ks[0], MANUFACTURERS.get(0xffff)
                    )
                    # TODO: Evaluate how to interpret the value of the company identifier...
                    return "{0}: {1} ({2})".format(self.address, mf, value)
        return "{0}: {1}".format(self.address, self.name)
