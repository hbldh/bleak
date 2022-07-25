"""
Advertisement Monitor
--------------------

This module contains types associated with the BlueZ D-Bus `advertisement
monitor api <https://github.com/bluez/bluez/blob/master/doc/advertisement-monitor-api.txt>`.
"""

import logging
from typing import Callable, Iterable, NamedTuple, Set, Tuple, Union, no_type_check

from dbus_next.service import ServiceInterface, dbus_property, method, PropertyAccess

from . import defs
from ...assigned_numbers import AdvertisementDataType


logger = logging.getLogger(__name__)


class OrPattern(NamedTuple):
    """
    BlueZ advertisement monitor or-pattern.

    https://github.com/bluez/bluez/blob/master/doc/advertisement-monitor-api.txt
    """

    start_position: int
    ad_data_type: AdvertisementDataType
    content_of_pattern: bytes


# Windows has a similar structure, so we allow generic tuple for cross-platform compatibility
OrPatternLike = Union[OrPattern, Tuple[int, AdvertisementDataType, bytes]]


class AdvertisementMonitor(ServiceInterface):
    """
    Implementation of the org.bluez.AdvertisementMonitor1 D-Bus interface.
    """

    def __init__(
        self,
        or_patterns: Iterable[OrPatternLike],
        on_device_found: Callable[[str], None],
    ):
        """
        Args:
            or_patterns:
                List of or patterns that will be returned by the ``Patterns`` property.
            on_device_found:
                Callback that will be called with the D-Bus device object path
                when an advertisement is received.
        """
        super().__init__(defs.ADVERTISEMENT_MONITOR_INTERFACE)
        # dbus_next marshaling requires list instead of tuple
        self._or_patterns = [list(p) for p in or_patterns]
        self._on_device_found = on_device_found
        self._seen_devices: Set[str] = set()

    @method()
    def Release(self):
        logger.debug("Release")

    @method()
    def Activate(self):
        logger.debug("Activate")

    # REVISIT: mypy is broke, so we have to add redundant @no_type_check
    # https://github.com/python/mypy/issues/6583

    @method()
    @no_type_check
    def DeviceFound(self, device: "o"):  # noqa: F821
        logger.debug("DeviceFound %s", device)

        # REVISIT: this will not catch advertisement data that changes like
        # active scanning does

        # only call callback once per device to avoid flood of callbacks
        if device not in self._seen_devices:
            self._seen_devices.add(device)
            self._on_device_found(device)

    @method()
    @no_type_check
    def DeviceLost(self, device: "o"):  # noqa: F821
        logger.debug("DeviceLost %s", device)

    @dbus_property(PropertyAccess.READ)
    @no_type_check
    def Type(self) -> "s":  # noqa: F821
        # this is currently the only type supported in BlueZ
        return "or_patterns"

    @dbus_property(PropertyAccess.READ, disabled=True)
    @no_type_check
    def RSSILowThreshold(self) -> "n":  # noqa: F821
        ...

    @dbus_property(PropertyAccess.READ, disabled=True)
    @no_type_check
    def RSSIHighThreshold(self) -> "n":  # noqa: F821
        ...

    @dbus_property(PropertyAccess.READ, disabled=True)
    @no_type_check
    def RSSILowTimeout(self) -> "q":  # noqa: F821
        ...

    @dbus_property(PropertyAccess.READ, disabled=True)
    @no_type_check
    def RSSIHighTimeout(self) -> "q":  # noqa: F821
        ...

    @dbus_property(PropertyAccess.READ, disabled=True)
    @no_type_check
    def RSSISamplingPeriod(self) -> "q":  # noqa: F821
        ...

    @dbus_property(PropertyAccess.READ)
    @no_type_check
    def Patterns(self) -> "a(yyay)":  # noqa: F821
        return self._or_patterns
