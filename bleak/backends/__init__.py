"""
Communicating with Bluetooth hardware requires calling OS-specific APIs. These
are abstracted as "backends" in Bleak.

The backend will be automatically selected based on the operating system Bleak
is running on. In some cases, this may also depend on a specific runtime, like
Pythonista on iOS.
"""

import enum
import os
import platform
import sys

from bleak.exc import BleakError


class BleakBackend(str, enum.Enum):
    """
    Identifiers for available built-in Bleak backends.

    .. versionadded:: 2.0
    """

    P4ANDROID = "p4android"
    """
    Python for Android backend.
    """

    BLUEZ_DBUS = "bluez_dbus"
    """
    BlueZ D-Bus backend for Linux.
    """

    PYTHONISTA_CB = "pythonista_cb"
    """
    Pythonista CoreBluetooth backend for iOS and macOS.
    """

    CORE_BLUETOOTH = "core_bluetooth"
    """
    CoreBluetooth backend for macOS.
    """

    WIN_RT = "win_rt"
    """
    Windows Runtime backend for Windows.
    """


def get_default_backend() -> BleakBackend:
    """
    Returns the preferred backend for the current platform/environment.

    .. versionadded:: 2.0
    """
    if os.environ.get("P4A_BOOTSTRAP") is not None:
        return BleakBackend.P4ANDROID

    if platform.system() == "Linux":
        return BleakBackend.BLUEZ_DBUS

    if sys.platform == "ios" and "Pythonista3.app" in sys.executable:
        # Must be resolved before checking for "Darwin" (macOS),
        # as both the Pythonista app for iOS and macOS
        # return "Darwin" from platform.system()
        return BleakBackend.PYTHONISTA_CB

    if platform.system() == "Darwin":
        return BleakBackend.CORE_BLUETOOTH

    if platform.system() == "Windows":
        return BleakBackend.WIN_RT

    raise BleakError(f"Unsupported platform: {platform.system()}")
