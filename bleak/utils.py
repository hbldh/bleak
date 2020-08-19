# -*- coding: utf-8 -*-


def mac_str_2_int(mac):
    """Convert colon separated hex string Bluetooth address to integer.

    Args:
        mac (str): A colon separated hex string Bluetooth address.

    Returns:
        Bluetooth address as integer.

    """
    return int(mac.replace(":", ""), 16)


def mac_int_2_str(mac):
    """Convert integer Bluetooth address to colon separated hex string.

    Args:
        mac (int): A positive integer.

    Returns:
        Bluetooth address as colon separated hex string.

    """
    m = hex(mac)[2:].upper().zfill(12)
    return ":".join([m[i : i + 2] for i in range(0, 12, 2)])
