import os
import platform
from bleak.backends.bluezdbus import check_bluez_version
from bleak.exc import BleakError

_on_rtd = os.environ.get("READTHEDOCS") == "True"
_on_ci = "CI" in os.environ

# Abstract classes, to allow typing and documentation to be specified
# independent of backend

class AbstractBleakScanner:
    pass

class AbstractBleakClient:
    pass

if _on_rtd:
    class BackendBleakScanner:
        pass
    class BackendBleakClient:
        pass
elif os.environ.get("P4A_BOOTSTRAP") is not None:
    from bleak.backends.p4android.scanner import (
        BleakScannerP4Android as BackendBleakScanner,
    )  # noqa: F401
    from bleak.backends.p4android.client import (
        BleakClientP4Android as BackEndBleakClient,
    )  # noqa: F401
elif platform.system() == "Linux":
    if not _on_ci and not check_bluez_version(5, 43):
        raise BleakError("Bleak requires BlueZ >= 5.43.")

    from bleak.backends.bluezdbus.scanner import (
        BleakScannerBlueZDBus as BackendBleakScanner,
    )  # noqa: F401
    from bleak.backends.bluezdbus.client import (
        BleakClientBlueZDBus as BackendBleakClient,
    )  # noqa: F401
elif platform.system() == "Darwin":
    try:
        from CoreBluetooth import CBPeripheral  # noqa: F401
    except Exception as ex:
        raise BleakError("Bleak requires the CoreBluetooth Framework") from ex

    from bleak.backends.corebluetooth.scanner import (
        BleakScannerCoreBluetooth as BackendBleakScanner,
    )  # noqa: F401
    from bleak.backends.corebluetooth.client import (
        BleakClientCoreBluetooth as BackendBleakClient,
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
        BleakScannerWinRT as BackendBleakScanner,
    )  # noqa: F401
    from bleak.backends.winrt.client import (
        BleakClientWinRT as BackendBleakClient,
    )  # noqa: F401

else:
    raise BleakError(f"Unsupported platform: {platform.system()}")

# Now let's tie together the abstract class and the backend implementation
class BleakScanner(AbstractBleakScanner, BackendBleakScanner):
    pass

class BleakClient(AbstractBleakClient, BackEndBleakClient):
    pass

# for backward compatibility
if not _on_rtd:
    discover = BleakScanner.discover
