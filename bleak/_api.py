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
    from bleak.backends.client import (
        BaseBleakClient as _BleakClientImplementation,
    )  # noqa: F401
elif os.environ.get("P4A_BOOTSTRAP") is not None:
    from bleak.backends.p4android.scanner import (
        BleakScannerP4Android as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.p4android.client import (
        BleakClientP4Android as _BleakClientImplementation,
    )  # noqa: F401
elif platform.system() == "Linux":

    from bleak.backends.bluezdbus.scanner import (
        BleakScannerBlueZDBus as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.bluezdbus.client import (
        BleakClientBlueZDBus as _BleakClientImplementation,
    )  # noqa: F401
elif platform.system() == "Darwin":
    try:
        from CoreBluetooth import CBPeripheral  # noqa: F401
    except Exception as ex:
        raise BleakError("Bleak requires the CoreBluetooth Framework") from ex

    from bleak.backends.corebluetooth.scanner import (
        BleakScannerCoreBluetooth as _BleakScannerImplementation,
    )  # noqa: F401
    from bleak.backends.corebluetooth.client import (
        BleakClientCoreBluetooth as _BleakClientImplementation,
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
    from bleak.backends.winrt.client import (
        BleakClientWinRT as _BleakClientImplementation,
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


class BleakClient(_BleakClientImplementation):
    """The interface for communicating with BLE devices.

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


# for backward compatibility
discover = BleakScanner.discover
