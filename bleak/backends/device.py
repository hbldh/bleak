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
      `Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisement` object, unless
      it is created with the Windows.Devices.Enumeration discovery method, then is is a
      `Windows.Devices.Enumeration.DeviceInformation`
    - When using Linux backend, `details` attribute is a
      dict with keys `path` which has the string path to the DBus device object and `props`
      which houses the properties dictionary of the D-Bus Device.
    - When using macOS backend, `details` attribute will be a CBPeripheral object
    """

    def __init__(self, address, name, details=None, **kwargs):
        self.address = address
        self.name = name if name else "Unknown"
        self.details = details
        self.metadata = kwargs

    @property
    def rssi(self):
        """Get the signal strength in dBm"""
        if isinstance(self.details, dict) and "props" in self.details:
            rssi = self.details["props"].get("RSSI", 0)  # Should not be set to 0...
        elif hasattr(self.details, "RawSignalStrengthInDBm"):
            rssi = self.details.RawSignalStrengthInDBm
        elif hasattr(self.details, "Properties"):
            rssi = {p.Key: p.Value for p in self.details.Properties}[
                "System.Devices.Aep.SignalStrength"
            ]
        else:
            rssi = None
        return int(rssi) if rssi is not None else None

    def __str__(self):
        if self.name == "Unknown":
            if "manufacturer_data" in self.metadata:
                ks = list(self.metadata["manufacturer_data"].keys())
                if len(ks):
                    mf = MANUFACTURERS.get(ks[0], MANUFACTURERS.get(0xFFFF))
                    value = self.metadata["manufacturer_data"].get(
                        ks[0], MANUFACTURERS.get(0xFFFF)
                    )
                    # TODO: Evaluate how to interpret the value of the company identifier...
                    return "{0}: {1} ({2})".format(self.address, mf, value)
        return "{0}: {1}".format(self.address, self.name)
