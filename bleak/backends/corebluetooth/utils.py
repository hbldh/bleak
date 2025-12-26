import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

from typing import Optional, overload

from CoreBluetooth import CBUUID
from Foundation import NSNumber, NSString

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


@overload
def to_optional_str(value: NSString) -> str: ...
@overload
def to_optional_str(value: None) -> None: ...


def to_optional_str(value: Optional[NSString]) -> Optional[str]:
    """Converts an NSString to a Python string or None.

    Args:
        value: The NSString or None.

    Returns:
        The Python string or None.
    """
    if value is None:
        return None

    return str(value)


@overload
def to_optional_int(value: NSNumber) -> int: ...
@overload
def to_optional_int(value: None) -> None: ...


def to_optional_int(value: Optional[NSNumber]) -> Optional[int]:
    """Converts an NSNumber to a Python int or None.

    Args:
        value: The NSNumber or None.

    Returns:
        The Python int or None.
    """
    if value is None:
        return None

    return int(value)
