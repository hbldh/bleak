import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

from CoreBluetooth import CBUUID

from bleak.uuids import normalize_uuid_str


def cb_uuid_to_str(uuid: CBUUID) -> str:
    """Converts a CoreBluetooth UUID to a Python string.

    If ``uuid`` is a 16-bit UUID, it is assumed to be a Bluetooth GATT UUID
    (``0000xxxx-0000-1000-8000-00805f9b34fb``).

    Args
        uuid: The UUID.

    Returns:
        The UUID as a lower case Python string (``xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx``)
    """
    return normalize_uuid_str(uuid.UUIDString())
