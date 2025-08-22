"""
-------------------------------
CoreBluetooth backend arguments
-------------------------------
"""

from collections.abc import Callable
from typing import Optional, TypedDict


class CBScannerArgs(TypedDict, total=False):
    """
    Platform-specific :class:`BleakScanner` args for the CoreBluetooth backend.
    """

    use_bdaddr: bool
    """
    If true, use Bluetooth address instead of UUID.

    .. warning:: This uses an undocumented IOBluetooth API to get the Bluetooth
        address and may break in the future macOS releases. `It is known to not
        work on macOS 10.15 <https://github.com/hbldh/bleak/issues/1286>`_.
    """


NotificationDiscriminator = Callable[[bytes], bool]


class CBStartNotifyArgs(TypedDict, total=False):
    """CoreBluetooth backend-specific dictionary of arguments for the
    :meth:`bleak.BleakClient.start_notify` method.
    """

    notification_discriminator: Optional[NotificationDiscriminator]
    """
    A function that takes a single argument of a characteristic value
    and returns ``True`` if the value is from a notification or
    ``False`` if the value is from a read response.

    .. seealso:: :ref:`cb-notification-discriminator` for more info.
    """
