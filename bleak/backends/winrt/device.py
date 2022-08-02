from bleak.backends.device import BLEDevice


class BLEDeviceWinRT(BLEDevice):
    """Class representing a BLE server detected during a `discover` call, Windows implementation.

    - When using Windows backend, `details` attribute is a
      ``Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisement`` object, unless
      it is created with the Windows.Devices.Enumeration discovery method, then is is a
      ``Windows.Devices.Enumeration.DeviceInformation``.
    """
    pass