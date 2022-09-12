# -*- coding: utf-8 -*-
import re

_address_separators = [":", "-"]
_address_regex = re.compile(
    rf"^([0-9A-Fa-f]{{2}}[{''.join(_address_separators)}]){{5}}([0-9A-Fa-f]{{2}})$"
)


def validate_address(address: str) -> bool:
    """Checks for validity of the given Bluetooth device address

    Args:
        address (str): Bluetooth device address to check

    Returns:
        bool: True if the given Bluetooth device address is valid
    """
    return _address_regex.match(address) is not None


def address_to_int(address: str) -> int:
    """Converts the Bluetooth device address string to its representing integer

    Args:
        address (str): Bluetooth device address to convert

    Returns:
        int: integer representation of the given Bluetooth device address
    """
    if not validate_address(address):
        raise ValueError("The given Bluetooth device address is not valid.")

    for char in _address_separators:
        address = address.replace(char, "")

    return int(address, base=16)
