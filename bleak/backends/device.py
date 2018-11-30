# -*- coding: utf-8 -*-
"""
Wrapper class for Bluetooth LE servers returned from calling
:py:meth:`bleak.discover`.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""


class BLEDevice(object):
    """A simple wrapper class representing a BLE server detected during
    a `discover` call.

    - When using Windows backend, `details` attribute is a
      `Windows.Devices.Enumeration.DeviceInformation` object.
    - When using Linux backend, `details` attribute is a
      string path to the DBus device object.
    - When using macOS backend, `details` attribute will be
      something else.

    """

    def __init__(self, address, name, details=None):
        self.address = address
        self.name = name if name else "Unknown"
        self.details = details

    def __str__(self):
        return "{0}: {1}".format(self.address, self.name)
