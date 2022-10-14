# -*- coding: utf-8 -*-
import re

from dbus_fast.constants import MessageType
from dbus_fast.message import Message

from ...exc import BleakError, BleakDBusError

_address_regex = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


def assert_reply(reply: Message):
    """Checks that a D-Bus message is a valid reply.

    Raises:
        BleakDBusError: if the message type is ``MessageType.ERROR``
        AssertionError: if the message type is not ``MessageType.METHOD_RETURN``
    """
    if reply.message_type == MessageType.ERROR:
        raise BleakDBusError(reply.error_name, reply.body)
    assert reply.message_type == MessageType.METHOD_RETURN


def validate_address(address):
    return _address_regex.match(address) is not None


def extract_service_handle_from_path(path):
    try:
        return int(path[-4:], 16)
    except Exception as e:
        raise BleakError(f"Could not parse service handle from path: {path}") from e


def bdaddr_from_device_path(device_path: str) -> str:
    """
    Scrape the Bluetooth address from a D-Bus device path.

    Args:
        device_path: The D-Bus object path of the device.

    Returns:
        A Bluetooth address as a string.
    """
    return ":".join(device_path[-17:].split("_"))
