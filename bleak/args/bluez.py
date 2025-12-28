"""
-----------------------
BlueZ backend arguments
-----------------------
"""

from typing import NamedTuple, TypedDict, Union

from bleak.assigned_numbers import AdvertisementDataType


class BlueZDiscoveryFilters(TypedDict, total=False):
    """
    Dictionary of arguments for the ``org.bluez.Adapter1.SetDiscoveryFilter``
    D-Bus method.

    https://github.com/bluez/bluez/blob/master/doc/org.bluez.Adapter.rst#void-setdiscoveryfilterdict-filter
    """

    UUIDs: list[str]
    """
    Filter by service UUIDs, empty means match _any_ UUID.

    Normally, the ``service_uuids`` argument of :class:`bleak.BleakScanner`
    is used instead.
    """
    RSSI: int
    """
    RSSI threshold value.
    """
    Pathloss: int
    """
    Pathloss threshold value.
    """
    Transport: str
    """
    Transport parameter determines the type of scan.

    This should not be used since it is required to be set to ``"le"``.
    """
    DuplicateData: bool
    """
    Disables duplicate detection of advertisement data.

    This does not affect the ``Filter Duplicates`` parameter of the ``LE Set Scan Enable``
    HCI command to the Bluetooth adapter!

    Although the default value for BlueZ is ``True``, Bleak sets this to ``False`` by default.
    """
    Discoverable: bool
    """
    Make adapter discoverable while discovering,
    if the adapter is already discoverable setting
    this filter won't do anything.
    """
    Pattern: str
    """
    Discover devices where the pattern matches
    either the prefix of the address or
    device name which is convenient way to limited
    the number of device objects created during a
    discovery.
    """


class OrPattern(NamedTuple):
    """
    BlueZ advertisement monitor or-pattern.

    https://github.com/bluez/bluez/blob/master/doc/org.bluez.AdvertisementMonitor.rst#arrayuint8-uint8-arraybyte-patterns-read-only-optional
    """

    start_position: int
    ad_data_type: AdvertisementDataType
    content_of_pattern: bytes


# Windows has a similar structure, so we allow generic tuple for cross-platform compatibility
OrPatternLike = Union[OrPattern, tuple[int, AdvertisementDataType, bytes]]


class BlueZScannerArgs(TypedDict, total=False):
    """
    :class:`BleakScanner` args that are specific to the BlueZ backend.
    """

    filters: BlueZDiscoveryFilters
    """
    Filters to pass to the adapter SetDiscoveryFilter D-Bus method.

    Only used for active scanning.
    """

    or_patterns: list[OrPatternLike]
    """
    Or patterns to pass to the AdvertisementMonitor1 D-Bus interface.

    Only used for passive scanning.
    """


class BlueZNotifyArgs(TypedDict, total=False):
    """
    :meth:`bleak.BleakClient.start_notify` method args that are specific to the
    BlueZ backend.

    .. versionadded:: 2.1
    """

    use_start_notify: bool
    """
    If true, use the "StartNotify" D-Bus method instead of "AcquireNotify" to
    subscribe to notifications.

    This is needed in rare cases to work around BlueZ quirks. For example, some
    peripherals may send notifications immediately after writing to the CCCD
    descriptor, before the write response is sent. In this case, "AcquireNotify"
    will miss the notification, whereas "StartNotify" will work correctly.
    """
