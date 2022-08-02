import os
import platform
from bleak.exc import BleakError
from bleak.backends.scanner import BaseBleakScanner
from bleak.backends.client import BaseBleakClient


_on_rtd = os.environ.get("READTHEDOCS") == "True"

if _on_rtd:
    from bleak.backends.scanner import (
        BaseBleakScanner as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.device import (
        BLEDevice as _BLEDeviceImplementation,
    )  # noqa: F401
    from bleak.backends.client import (
        BaseBleakClient as _BleakClientImplementation,
    )  # noqa: F401
    from bleak.backends.service import (
        BleakGATTService as _BleakGATTServiceImplementation,
    )  # noqa: F401
    from bleak.backends.characteristic import (
        BleakGATTCharacteristic as _BleakGATTCharacteristicImplementation,
    )  # noqa: F401
    from bleak.backends.descriptor import (
        BleakGATTDescriptor as _BleakGATTDescriptorImplementation,
    )  # noqa: F401
elif os.environ.get("P4A_BOOTSTRAP") is not None:
    from bleak.backends.p4android.scanner import (
        BleakScannerP4Android as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.device import (
        BLEDevice as _BLEDeviceImplementation,
    )  # noqa: F401
    from bleak.backends.p4android.client import (
        BleakClientP4Android as _BleakClientImplementation,
    )  # noqa: F401
    from bleak.backends.p4android.service import (
        BleakGATTServiceP4Android as _BleakGATTServiceImplementation,
    )  # noqa: F401
    from bleak.backends.p4android.characteristic import (
        BleakGATTCharacteristicP4Android as _BleakGATTCharacteristicImplementation,
    )  # noqa: F401
    from bleak.backends.p4android.descriptor import (
        BleakGATTDescriptorP4Android as _BleakGATTDescriptorImplementation,
    )  # noqa: F401
elif platform.system() == "Linux":

    from bleak.backends.bluezdbus.scanner import (
        BleakScannerBlueZDBus as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.device import (
        BLEDevice as _BLEDeviceImplementation,
    )  # noqa: F401
    from bleak.backends.bluezdbus.client import (
        BleakClientBlueZDBus as _BleakClientImplementation,
    )  # noqa: F401
    from bleak.backends.bluezdbus.service import (
        BleakGATTServiceBlueZDBus as _BleakGATTServiceImplementation,
    )  # noqa: F401
    from bleak.backends.bluezdbus.characteristic import (
        BleakGATTCharacteristicBlueZDBus as _BleakGATTCharacteristicImplementation,
    )  # noqa: F401
    from bleak.backends.bluezdbus.descriptor import (
        BleakGATTDescriptorBlueZDBus as _BleakGATTDescriptorImplementation,
    )  # noqa: F401
elif platform.system() == "Darwin":
    try:
        from CoreBluetooth import CBPeripheral  # noqa: F401
    except Exception as ex:
        raise BleakError("Bleak requires the CoreBluetooth Framework") from ex

    from bleak.backends.corebluetooth.scanner import (
        BleakScannerCoreBluetooth as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.corebluetooth.device import (
        BLEDeviceCoreBluetooth as _BLEDeviceImplementation,
    )  # noqa: F401
    from bleak.backends.corebluetooth.client import (
        BleakClientCoreBluetooth as _BleakClientImplementation,
    )  # noqa: F401
    from bleak.backends.corebluetooth.service import (
        BleakGATTServiceCoreBluetooth as _BleakGATTServiceImplementation,
    )  # noqa: F401
    from bleak.backends.corebluetooth.characteristic import (
        BleakGATTCharacteristicCoreBluetooth as _BleakGATTCharacteristicImplementation,
    )  # noqa: F401
    from bleak.backends.corebluetooth.descriptor import (
        BleakGATTDescriptorCoreBluetooth as _BleakGATTDescriptorImplementation,
    )  # noqa: F401
elif platform.system() == "Windows":
    # Requires Windows 10 Creators update at least, i.e. Window 10.0.16299
    _vtup = platform.win32_ver()[1].split(".")
    if int(_vtup[0]) != 10:
        raise BleakError(
            "Only Windows 10 is supported. Detected was {0}".format(
                platform.win32_ver()
            )
        )

    if (int(_vtup[1]) == 0) and (int(_vtup[2]) < 16299):
        raise BleakError(
            "Requires at least Windows 10 version 0.16299 (Fall Creators Update)."
        )

    from bleak.backends.winrt.scanner import (
        BleakScannerWinRT as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.device import (
        BLEDevice as _BLEDeviceImplementation,
    )  # noqa: F401
    from bleak.backends.winrt.client import (
        BleakClientWinRT as _BleakClientImplementation,
    )  # noqa: F401
    from bleak.backends.winrt.service import (
        BleakGATTServiceWinRT as _BleakGATTServiceImplementation,
    )  # noqa: F401
    from bleak.backends.winrt.characteristic import (
        BleakGATTCharacteristicWinRT as _BleakGATTCharacteristicImplementation,
    )  # noqa: F401
    from bleak.backends.winrt.descriptor import (
        BleakGATTDescriptorWinRT as _BleakGATTDescriptorImplementation,
    )  # noqa: F401
else:
    raise BleakError(f"Unsupported platform: {platform.system()}")

# Now let's tie together the abstract class and the backend implementation
class BleakScanner(_BleakScannerImplementation):
    """
    Interface for Bleak Bluetooth LE Scanners.

    The actual implementation is dependent on the backend used, and some methods (notably the
    constructor) may have additional optional arguments.


    Args:
        detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
        service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received.
        scanning_mode:
            Set to "passive" to avoid the "active" scanning mode.
    """

    pass


class BLEDevice(_BLEDeviceImplementation):
    """Class representing a BLE server detected during a `discover` call.

    It is usually instantiated by bleak and only inspected by the user code. It contains a
    BleakGATTServiceCollection describing the services exported by the BLE server, and some
    backend-dependent details:

    - When using Windows backend, `details` attribute is a
      ``Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisement`` object, unless
      it is created with the Windows.Devices.Enumeration discovery method, then is is a
      ``Windows.Devices.Enumeration.DeviceInformation``.
    - When using Linux backend, ``details`` attribute is a
      dict with keys ``path`` which has the string path to the DBus device object and ``props``
      which houses the properties dictionary of the D-Bus Device.
    - When using macOS backend, ``details`` attribute will be a CBPeripheral object.
    """

    pass


from bleak.backends.scanner import AdvertisementData
from bleak.backends.scanner import AdvertisementDataCallback
from bleak.backends.scanner import AdvertisementDataFilter


class BleakClient(_BleakClientImplementation):
    """The interface for communicating with BLE servers.

    The actual implementation is dependent on the backend used, and some the constructor and some methods may have
    additional optional arguments.

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.

    Keyword Args:
        timeout (float): Timeout for required ``discover`` call. Defaults to 10.0.
        disconnected_callback (callable): Callback that will be scheduled in the
            event loop when the client is disconnected. The callable must take one
            argument, which will be this client object.
    """

    pass


from bleak.backends.service import (
    BleakGATTServiceCollection as _BleakGATTServiceCollectionImplementation,
)


class BleakGATTServiceCollection(_BleakGATTServiceCollectionImplementation):
    """A BleakGATTServiceCollection is the collection of all services (and characteristics) implemented by a BLEDevice.

    It is usually instantiated by bleak and only inspected by the user code. There are different implementations
    for different backends, but these present the same interface to user code.
    """


class BleakGATTService(_BleakGATTServiceImplementation):
    """A BleakGATTService is a collection of BleakGATTCharacteristic objects that somehow belong together.

    It is usually instantiated by bleak and only inspected by the user code. There are different implementations
    for different backends, but these present the same interface to user code.
    """


class BleakGATTCharacteristic(_BleakGATTCharacteristicImplementation):
    """A BleakGATTCharacteristic can be thought of as the name or address of a variable in the service.

    It can be passed to BleakClient methods to read, write or otherwise access those variables. It may contain
    BleakGATTDescriptor objects that further describe the variable and its values.

    It is usually instantiated by bleak and only inspected by the user code. There are different implementations
    for different backends, but these present the same interface to user code.
    """

    pass


class BleakGATTDescriptor(_BleakGATTDescriptorImplementation):
    """A BleakGATTDescriptor is attached to a BleakGATTCharacteristic and describes attributes of that characteristic.

    Attributes could be things like the human-readable name, or its presentation format.

    It is usually instantiated by bleak and only inspected by the user code. There are different implementations
    for different backends, but these present the same interface to user code.
    """

    pass
