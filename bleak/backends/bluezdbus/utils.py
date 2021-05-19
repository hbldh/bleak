# -*- coding: utf-8 -*-
import re
from typing import Any, Dict

from dbus_next.constants import MessageType
from dbus_next.message import Message
from dbus_next.signature import Variant

from bleak import BleakError
from bleak.exc import BleakDBusError

_mac_address_regex = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


def assert_reply(reply: Message):
    """Checks that a D-Bus message is a valid reply.

    Raises:
        BleakDBusError: if the message type is ``MessageType.ERROR``
        AssentationError: if the message type is not ``MessageType.METHOD_RETURN``
    """
    if reply.message_type == MessageType.ERROR:
        raise BleakDBusError(reply.error_name, reply.body)
    assert reply.message_type == MessageType.METHOD_RETURN


def validate_mac_address(address):
    return _mac_address_regex.match(address) is not None


def unpack_variants(dictionary: Dict[str, Variant]) -> Dict[str, Any]:
    """Recursively unpacks all ``Variant`` types in a dictionary to their
    corresponding Python types.

    ``dbus-next`` doesn't automatically do this, so this needs to be called on
    all dictionaries ("a{sv}") returned from D-Bus messages.
    """
    unpacked = {}
    for k, v in dictionary.items():
        v = v.value if isinstance(v, Variant) else v
        if isinstance(v, dict):
            v = unpack_variants(v)
        elif isinstance(v, list):
            v = [x.value if isinstance(x, Variant) else x for x in v]
        unpacked[k] = v
    return unpacked


def extract_service_handle_from_path(path):
    try:
        return int(path[-4:], 16)
    except Exception as e:
        raise BleakError(f"Could not parse service handle from path: {path}") from e
