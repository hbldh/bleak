"""
Bluetooth Assigned Numbers
--------------------------

This module contains useful assigned numbers from the Bluetooth spec.

See <https://www.bluetooth.com/specifications/assigned-numbers/>.
"""

from enum import IntEnum
from typing import Literal


class AdvertisementDataType(IntEnum):
    """
    Generic Access Profile advertisement data types.

    `Source <https://btprodspecificationrefs.blob.core.windows.net/assigned-numbers/Assigned%20Number%20Types/Generic%20Access%20Profile.pdf>`.

    .. versionadded:: 0.15
    """

    FLAGS = 0x01
    INCOMPLETE_LIST_SERVICE_UUID16 = 0x02
    COMPLETE_LIST_SERVICE_UUID16 = 0x03
    INCOMPLETE_LIST_SERVICE_UUID32 = 0x04
    COMPLETE_LIST_SERVICE_UUID32 = 0x05
    INCOMPLETE_LIST_SERVICE_UUID128 = 0x06
    COMPLETE_LIST_SERVICE_UUID128 = 0x07
    SHORTENED_LOCAL_NAME = 0x08
    COMPLETE_LOCAL_NAME = 0x09
    TX_POWER_LEVEL = 0x0A
    CLASS_OF_DEVICE = 0x0D

    SERVICE_DATA_UUID16 = 0x16
    SERVICE_DATA_UUID32 = 0x20
    SERVICE_DATA_UUID128 = 0x21

    MANUFACTURER_SPECIFIC_DATA = 0xFF


# NOTE: these must match BlueZ name mapping
CharacteristicPropertyName = Literal[
    "broadcast",
    "read",
    "write-without-response",
    "write",
    "notify",
    "indicate",
    "authenticated-signed-writes",
    "extended-properties",
    "reliable-write",
    "writable-auxiliaries",
    "encrypt-read",
    "encrypt-write",
    # "encrypt-notify" and "encrypt-indicate" are server-only
    "encrypt-authenticated-read",
    "encrypt-authenticated-write",
    # "encrypt-authenticated-notify", "encrypt-authenticated-indicate",
    # "secure-read", "secure-write", "secure-notify", "secure-indicate"
    # are server-only
    "authorize",
]

CHARACTERISTIC_PROPERTIES: dict[int, CharacteristicPropertyName] = {
    0x1: "broadcast",
    0x2: "read",
    0x4: "write-without-response",
    0x8: "write",
    0x10: "notify",
    0x20: "indicate",
    0x40: "authenticated-signed-writes",
    0x80: "extended-properties",
    0x100: "reliable-write",
    0x200: "writable-auxiliaries",
}


def gatt_char_props_to_strs(
    props: int,
) -> frozenset[CharacteristicPropertyName]:
    """
    Convert a GATT characteristic properties bitmask to a set of strings.

    Args:
        props: The GATT characteristic properties bitmask.

    Returns:
        A set of strings representing the GATT characteristic properties.
    """
    return frozenset(
        CHARACTERISTIC_PROPERTIES[i] for i in (1 << n for n in range(16)) if props & i
    )
