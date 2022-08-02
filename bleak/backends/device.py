# -*- coding: utf-8 -*-
"""
Wrapper class for Bluetooth LE servers returned from calling
:py:meth:`bleak.discover`.

Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>

"""
from ._manufacturers import MANUFACTURERS
from bleak import abstract_api


class BLEDevice(abstract_api.BLEDevice):
    """Class representing a BLE server detected during a `discover` call.


    """

    def __init__(self, address, name, details=None, rssi=0, **kwargs):
        """Should not be called by end user, only by bleak itself"""
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
