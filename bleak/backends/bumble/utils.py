# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Victor Chavez
from bumble.core import UUID


def bumble_uuid_to_str(uuid: UUID) -> str:
    """
    Converts a native Bumble UUID to a standard string representation.
    Bumble's string representation (`__str__`) is non-standard, and its byte representation
    (`uuid_bytes`) is in reverse order. This function corrects these issues to provide a
    consistent and standard UUID string format.

    Example for a Bumble shortened 16-bit UUID:
        Bumble UUID string representation: 'UUID-16:1800 (Generic Access)'
        Bumble UUID bytes representation: b'\x00\x18'

    Args:
        uuid (UUID): The Bumble UUID object to be converted.

    Returns:
        str: The standard string representation of the UUID.

    """
    # Convert bytes to hex string, reverse the order, and join back as a string
    normalized_uuid = "".join([f"{b:02X}" for b in uuid.uuid_bytes[::-1]])
    return normalized_uuid
