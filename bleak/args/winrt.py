"""
-----------------------
WinRT backend arguments
-----------------------
"""

from typing import Literal, TypedDict


class WinRTClientArgs(TypedDict, total=False):
    """
    Windows-specific arguments for :class:`BleakClient`.
    """

    address_type: Literal["public", "random"]
    """
    Can either be ``"public"`` or ``"random"``, depending on the required address
    type needed to connect to your device.
    """

    use_cached_services: bool
    """
    ``True`` allows Windows to fetch the services, characteristics and descriptors
    from the Windows cache instead of reading them from the device. Can be very
    much faster for known, unchanging devices, but not recommended for DIY peripherals
    where the GATT layout can change between connections.

    ``False`` will force the attribute database to be read from the remote device
    instead of using the OS cache.

    If omitted, the OS Bluetooth stack will do what it thinks is best.
    """

    retry_on_services_changed: bool
    """
    ``True`` restarts getting the services, characteristics and descriptors if the
    device reports that its services changed while they are being read, e.g. on the
    first connection after a firmware update. See the remarks on
    `GattServicesChanged <https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothledevice.gattserviceschanged>`_.

    The restart cancels the pending request to the OS, which can leave the Windows
    Bluetooth stack in a bad state on some systems, so this is disabled by default.

    .. versionadded:: 3.2
    """
