import os
import platform
import sys
from dataclasses import dataclass

from bleak.backends.client import BaseBleakClient
from bleak.backends.scanner import BaseBleakScanner
from bleak.exc import BleakError


@dataclass(frozen=True)
class BleakBackendProvider:
    client_type: type[BaseBleakClient]
    scanner_type: type[BaseBleakScanner]


def get_backend() -> BleakBackendProvider:
    """
    Gets the platform-specific backend provider.
    """
    if sys.platform == "android" and os.environ.get("P4A_BOOTSTRAP") is not None:
        from bleak.backends.p4android.client import BleakClientP4Android
        from bleak.backends.p4android.scanner import BleakScannerP4Android

        return BleakBackendProvider(
            client_type=BleakClientP4Android,
            scanner_type=BleakScannerP4Android,
        )

    if sys.platform == "linux":
        from bleak.backends.bluezdbus.client import BleakClientBlueZDBus
        from bleak.backends.bluezdbus.scanner import BleakScannerBlueZDBus

        return BleakBackendProvider(
            client_type=BleakClientBlueZDBus,
            scanner_type=BleakScannerBlueZDBus,
        )

    if sys.platform == "ios" and "Pythonista3.app" in sys.executable:
        # Must be resolved before checking for "Darwin" (macOS),
        # as both the Pythonista app for iOS and macOS
        # return "Darwin" from platform.system()
        try:
            from bleak_pythonista import (
                BleakClientPythonistaCB,
                BleakScannerPythonistaCB,
            )

            return BleakBackendProvider(
                client_type=BleakClientPythonistaCB,
                scanner_type=BleakScannerPythonistaCB,
            )
        except ImportError as e:
            raise ImportError(
                "Ensure you have `bleak-pythonista` package installed."
            ) from e

    if sys.platform == "darwin":
        from bleak.backends.corebluetooth.client import BleakClientCoreBluetooth
        from bleak.backends.corebluetooth.scanner import BleakScannerCoreBluetooth

        return BleakBackendProvider(
            client_type=BleakClientCoreBluetooth,
            scanner_type=BleakScannerCoreBluetooth,
        )

    if sys.platform == "win32":
        from bleak.backends.winrt.client import BleakClientWinRT
        from bleak.backends.winrt.scanner import BleakScannerWinRT

        return BleakBackendProvider(
            client_type=BleakClientWinRT,
            scanner_type=BleakScannerWinRT,
        )

    raise BleakError(f"Unsupported platform: {platform.system()}")
