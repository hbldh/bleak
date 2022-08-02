import os
import platform
from bleak.exc import BleakError
from bleak.backends.scanner import BaseBleakScanner
from bleak.backends.client import BaseBleakClient


_on_rtd = os.environ.get("READTHEDOCS") == "True"

if _on_rtd:
    from bleak.abstract_api import (
        AbstractBleakScanner as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.abstract_api import (
        BLEDevice as _BLEDeviceImplementation,
    )  # noqa: F401
    from bleak.abstract_api import (
        AbstractBleakClient as _BleakClientImplementation,
    )  # noqa: F401
    from bleak.abstract_api import (
        BleakGATTService as _BleakGATTServiceImplementation,
    )  # noqa: F401
    from bleak.abstract_api import (
        BleakGATTCharacteristic as _BleakGATTCharacteristicImplementation,
    )  # noqa: F401
    from bleak.abstract_api import (
        BleakGATTDescriptor as _BleakGATTDescriptorImplementation,
    )  # noqa: F401
elif os.environ.get("P4A_BOOTSTRAP") is not None:
    from bleak.backends.p4android.scanner import (
        BleakScannerP4Android as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.p4android.device import (
        BLEDeviceP4Android as _BLEDeviceImplementation,
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
    from bleak.backends.bluezdbus.device import (
        BLEDeviceBlueZDBus as _BLEDeviceImplementation,
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
    from bleak.backends.winrt.device import (
        BLEDeviceWinRT as _BLEDeviceImplementation,
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
    """Interface for Bleak Bluetooth LE Scanners.

    A BleakScanner can be used as an asynchronous context manager in which case it automatically
    starts and stops scanning.

    The actual implementation is dependent on the backend used, and the
    constructor may have additional optional arguments.

    :param detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
    :type detection_callback: Optional[Callable[[BLEDevice, AdvertisementData], Optional[Awaitable[NoneType]]]]
    :param service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received.
    :type service_uuids: Optional[List[str]]
    :param scanning_mode:
            Set to "passive" to avoid the "active" scanning mode.
    :type scanning_mode: Literal['active', 'passive']
    """

    pass


class BLEDevice(_BLEDeviceImplementation):
    __doc__ = _BLEDeviceImplementation.__doc__
    pass


if _on_rtd:
    from bleak.abstract_api import AdvertisementData as AbstractAdvertisementData

    class AdvertisementData(AbstractAdvertisementData):
        pass

    from bleak.abstract_api import AdvertisementDataCallback
    from bleak.abstract_api import AdvertisementDataFilter
else:
    from bleak.backends.scanner import AdvertisementData
    from bleak.backends.scanner import AdvertisementDataCallback
    from bleak.backends.scanner import AdvertisementDataFilter


class BleakClient(_BleakClientImplementation):
    """API for connecting to a BLE server and communicating with it.

    A BleakClient can be used as an asynchronous context manager in which case it automatically
    connects and disconnects.

    The actual implementation is dependent on the backend used, and the constructor may have
    additional optional arguments.

    :param address_or_ble_device: The server to connect to, specified as BLEDevice or backend-dependent Bluetooth address.
    :type address_or_ble_device: Union[BLEDevice, str]
    :param timeout: Timeout for required ``discover`` call. Defaults to 10.0.
    :type timeout: float
    :param disconnected_callback: Callback that will be scheduled in the
            event loop when the client is disconnected.
    :type disconnected_callback: Callable[[BleakClient], None]
    """

    pass


from bleak.abstract_api import BleakGATTServiceCollection


class BleakGATTService(_BleakGATTServiceImplementation):
    __doc__ = _BleakGATTServiceImplementation.__doc__


class BleakGATTCharacteristic(_BleakGATTCharacteristicImplementation):
    __doc__ = _BleakGATTCharacteristicImplementation.__doc__


class BleakGATTDescriptor(_BleakGATTDescriptorImplementation):
    __doc__ = _BleakGATTDescriptorImplementation.__doc__

