"""
Advertisement Monitor
---------------------

This module contains types associated with the BlueZ D-Bus `advertisement
monitor api <https://github.com/bluez/bluez/blob/master/doc/org.bluez.AdvertisementMonitor.rst>`.
"""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import logging
from collections.abc import Iterable
from typing import Any, no_type_check
from warnings import warn

from dbus_fast import PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property, method

from bleak.args.bluez import OrPattern as _OrPattern
from bleak.args.bluez import OrPatternLike as _OrPatternLike
from bleak.backends.bluezdbus import defs

logger = logging.getLogger(__name__)

_DEPRECATED: dict[str, Any] = {
    "OrPattern": _OrPattern,
    "OrPatternLike": _OrPatternLike,
}


def __getattr__(name: str):
    if value := _DEPRECATED.get(name):
        warn(
            f"importing {name} from bleak.backends.bluezdbus.advertisement_monitor is deprecated, use bleak.args.bluez instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class AdvertisementMonitor(ServiceInterface):
    """
    Implementation of the org.bluez.AdvertisementMonitor1 D-Bus interface.

    The BlueZ advertisement monitor API design seems to be just for device
    presence (is it in range or out of range), but this isn't really what
    we want in Bleak, we want to monitor changes in advertisement data, just
    like in active scanning.

    So the only thing we are using here is the "or_patterns" since it is
    currently required, but really we don't need that either. Hopefully an
    "all" "Type" could be added to BlueZ in the future.
    """

    def __init__(
        self,
        or_patterns: Iterable[_OrPatternLike],
    ):
        """
        Args:
            or_patterns:
                List of or patterns that will be returned by the ``Patterns`` property.
        """
        super().__init__(defs.ADVERTISEMENT_MONITOR_INTERFACE)
        # dbus_fast marshaling requires list instead of tuple
        self._or_patterns = [list(p) for p in or_patterns]

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
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("DeviceFound %s", device)

    @method()
    @no_type_check
    def DeviceLost(self, device: "o"):  # noqa: F821
        if logger.isEnabledFor(logging.DEBUG):
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
