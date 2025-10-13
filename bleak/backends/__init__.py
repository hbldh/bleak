import enum
import os
import platform
import sys

from bleak.exc import BleakError


class BleakBackend(enum.Enum):
    P4Android = enum.auto()
    """
    Python for Android backend.
    """

    BlueZDBus = enum.auto()
    """
    BlueZ D-Bus backend for Linux.
    """

    PythonistaCB = enum.auto()
    """
    Pythonista CoreBluetooth backend for iOS and macOS.
    """

    CoreBluetooth = enum.auto()
    """
    CoreBluetooth backend for macOS.
    """

    WinRT = enum.auto()
    """
    Windows Runtime backend for Windows.
    """


def get_backend() -> BleakBackend:
    """
    Returns the preferred backend for the current platform/environment.
    """
    if os.environ.get("P4A_BOOTSTRAP") is not None:
        return BleakBackend.P4Android

    if platform.system() == "Linux":
        return BleakBackend.BlueZDBus

    if sys.platform == "ios" and "Pythonista3.app" in sys.executable:
        # Must be resolved before checking for "Darwin" (macOS),
        # as both the Pythonista app for iOS and macOS
        # return "Darwin" from platform.system()
        return BleakBackend.PythonistaCB

    if platform.system() == "Darwin":
        return BleakBackend.CoreBluetooth

    if platform.system() == "Windows":
        return BleakBackend.WinRT

    raise BleakError(f"Unsupported platform: {platform.system()}")
