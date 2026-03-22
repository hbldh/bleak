import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import os
import re
from typing import Optional

from dbus_fast.auth import AuthExternal
from dbus_fast.constants import MessageType
from dbus_fast.message import Message

from bleak.backends.bluezdbus import defs
from bleak.exc import (
    BleakDBusError,
    BleakError,
    BleakGATTProtocolError,
    BleakGATTProtocolErrorCode,
)


def assert_reply(reply: Message) -> None:
    """Checks that a D-Bus message is a valid reply.

    Raises:
        BleakDBusError: if the message type is ``MessageType.ERROR``
        AssertionError: if the message type is not ``MessageType.METHOD_RETURN``
    """
    if reply.message_type == MessageType.ERROR:
        assert reply.error_name
        raise BleakDBusError(reply.error_name, reply.body)
    assert reply.message_type == MessageType.METHOD_RETURN


def assert_gatt_reply(reply: Message, start_notify: bool = False) -> None:
    """
    Checks that a D-Bus message is a valid reply.

    Like :func:`assert_reply`, but has special handling for GATT protocol errors.

    Args:
        reply: The D-Bus message to check.
        start_notify: Whether this reply is for a StartNotify call.

    Raises:
        BleakGATTProtocolError: for specific GATT protocol errors.
        BleakDBusError: if the message type is ``MessageType.ERROR``
        AssertionError: if the message type is not ``MessageType.METHOD_RETURN``
    """

    # BlueZ has specific errors for some GATT protocol errors, so we
    # have to turn them back into the generic BleakGATTProtocolError
    # with the correct code. See create_gatt_dbus_error() in BlueZ source.

    if reply.error_name == defs.BLUEZ_ERROR_NOT_PERMITTED:
        # Same error is used for both read and write not permitted, so we have
        # to use the message to discriminate.
        if reply.body and reply.body[0] == "Read not permitted":
            raise BleakGATTProtocolError(BleakGATTProtocolErrorCode.READ_NOT_PERMITTED)

        if reply.body and reply.body[0] == "Write not permitted":
            raise BleakGATTProtocolError(BleakGATTProtocolErrorCode.WRITE_NOT_PERMITTED)

        # REVISIT: could also be "Not paired" which could be any of:
        # INSUFFICIENT_AUTHENTICATION, INSUFFICIENT_ENCRYPTION, or
        # INSUFFICIENT_ENCRYPTION_KEY_SIZE

    # "StartNotify" will return BLUEZ_ERROR_NOT_SUPPORTED if the characteristic
    # does not support notifications before even trying, so it is not a GATT
    # error in this case.
    if not start_notify and reply.error_name == defs.BLUEZ_ERROR_NOT_SUPPORTED:
        raise BleakGATTProtocolError(BleakGATTProtocolErrorCode.REQUEST_NOT_SUPPORTED)

    if reply.error_name == defs.BLUEZ_ERROR_NOT_AUTHORIZED:
        raise BleakGATTProtocolError(
            BleakGATTProtocolErrorCode.INSUFFICIENT_AUTHORIZATION
        )

    if reply.error_name == defs.BLUEZ_ERROR_INVALID_ARGUMENT:
        if reply.body and reply.body[0] == "Invalid offset":
            raise BleakGATTProtocolError(BleakGATTProtocolErrorCode.INVALID_OFFSET)

        if reply.body and reply.body[0] == "Invalid Length":
            raise BleakGATTProtocolError(
                BleakGATTProtocolErrorCode.INVALID_ATTRIBUTE_VALUE_LENGTH
            )

    if reply.error_name == defs.BLUEZ_ERROR_IMPROPERLY_CONFIGURED:
        raise BleakGATTProtocolError(
            BleakGATTProtocolErrorCode.CCCD_IMPROPERLY_CONFIGURED
        )

    if (
        reply.error_name == defs.BLUEZ_ERROR_FAILED
        and reply.body
        and (
            # Unfortunately, BlueZ makes us scrape the string to get the
            # error code in this case.
            match := re.match(
                r"^Operation failed with ATT error: (0x[0-9a-fA-F]+)",
                reply.body[0],
            )
        )
    ):
        raise BleakGATTProtocolError(
            BleakGATTProtocolErrorCode(int(match.group(1), 16))
        )

    assert_reply(reply)


def extract_service_handle_from_path(path: str) -> int:
    try:
        return int(path[-4:], 16)
    except Exception as e:
        raise BleakError(f"Could not parse service handle from path: {path}") from e


def device_path_from_characteristic_path(characteristic_path: str) -> str:
    """
    Scrape the device path from a D-Bus characteristic path.

    Args:
        characteristic_path: The D-Bus object path of the characteristic.

    Returns:
        A D-Bus object path of the device.
    """
    # /org/bluez/hci1/dev_FA_23_9D_AA_45_46/service000c/char000d
    return characteristic_path[:-21]


def get_dbus_authenticator() -> Optional[AuthExternal]:
    uid = None
    try:
        uid = int(os.environ.get("BLEAK_DBUS_AUTH_UID", ""))
    except ValueError:
        pass

    auth = None
    if uid is not None:
        auth = AuthExternal(uid=uid)

    return auth
