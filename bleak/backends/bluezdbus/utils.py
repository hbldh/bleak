# -*- coding: utf-8 -*-
import re
from typing import Any, Dict

from dbus_next.signature import Variant


_mac_address_regex = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


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
