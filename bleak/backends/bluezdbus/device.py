from bleak.backends.device import BLEDevice


class BLEDeviceBlueZDBus(BLEDevice):
    """Class representing a BLE server detected during a `discover` call, BlueZ implementation.

    - When using Linux backend, ``details`` attribute is a
      dict with keys ``path`` which has the string path to the DBus device object and ``props``
      which houses the properties dictionary of the D-Bus Device.
    """

    pass
