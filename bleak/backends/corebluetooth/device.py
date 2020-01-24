# -*- coding: utf-8 -*-
from bleak.backends._manufacturers import MANUFACTURERS

from Foundation import NSDictionary


from bleak.backends.device import BLEDevice


class BLEDeviceCoreBluetooth(BLEDevice):
    """
    A CoreBlutooth class representing a BLE server detected during
    a `discover` call.

    - The `details` attribute will be a CBPeripheral object.

    - The `metadata` keys are more or less part of the crossplattform interface.

    - Note: Take care not to rely on any reference to `advertisementData` and
      it's data as lower layers of the corebluetooth stack can change it. i.e.
      only valid/trusted in callback(s) or if copied.

    - AdvertisementData fields/keys that might be of interest:
      - kCBAdvDataAppleMfgData
      - kCBAdvDataChannel
      - kCBAdvDataManufacturerData
      - kCBAdvDataIsConnectable
      - kCBAdvDataChannel
      - kCBAdvDataAppleMfgData
      - kCBAdvDataTxPowerLevel
      - kCBAdvDataLocalName
      - kCBAdvDataServiceUUIDs
      - kCBAdvDataManufacturerData
    """

    def __init__(self, *args, **kwargs):
        super(BLEDeviceCoreBluetooth, self).__init__(*args, **kwargs)
        self.metadata = {}
        self._rssi = kwargs.get("rssi")

    def _update(self, advertisementData: NSDictionary):
        self._update_uuids(advertisementData)
        self._update_manufacturer(advertisementData)

    def _update_uuids(self, advertisementData: NSDictionary):
        cbuuids = advertisementData.get("kCBAdvDataServiceUUIDs", [])
        if not cbuuids:
            return
        # converting to lower case to match other platforms
        self.metadata["uuids"] = [str(u).lower() for u in cbuuids]

    def _update_manufacturer(self, advertisementData: NSDictionary):
        mfg_bytes = advertisementData.get("kCBAdvDataManufacturerData")
        if not mfg_bytes:
            return

        mfg_id = int.from_bytes(mfg_bytes[0:2], byteorder="little")
        mfg_val = bytes(mfg_bytes[2:])
        self.metadata["manufacturer_data"] = {mfg_id: mfg_val}

    @property
    def rssi(self):
        return self._rssi


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

