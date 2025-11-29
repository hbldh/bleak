# Created on 2018-04-23 by hbldh <henrik.blidh@nedomkull.com>
"""
Wrapper class for Bluetooth LE servers returned from calling
:py:meth:`bleak.discover`.
"""


from typing import Any, Optional
from warnings import warn


class BLEDevice:
    """
    A simple wrapper class representing a BLE server detected during scanning.
    """

    __slots__ = ("address", "name", "details")

    def __init__(self, address: str, name: Optional[str], details: Any, **kwargs: Any):
        #: The Bluetooth address of the device on this machine (UUID on macOS).
        self.address = address
        #: The operating system name of the device (not necessarily the local name
        #: from the advertising data), suitable for display to the user.
        self.name = name
        #: The OS native details required for connecting to the device.
        self.details = details

        if kwargs:
            warn(
                "Passing additional arguments for BLEDevice is deprecated and has no effect.",
                DeprecationWarning,
                stacklevel=2,
            )

    def __str__(self):
        return f"{self.address}: {self.name}"

    def __repr__(self):
        return f"BLEDevice({self.address}, {self.name})"
