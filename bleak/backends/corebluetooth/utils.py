from Foundation import NSData
from CoreBluetooth import CBUUID


def cb_uuid_to_str(_uuid: CBUUID) -> str:
    """Converts a CoreBluetooth UUID to a Python string.

    If ``_uuid`` is a 16-bit UUID, it is assumed to be a Bluetooth GATT UUID
    (``0000xxxx-0000-1000-8000-00805f9b34fb``).

    Args
        _uuid: The UUID.

    Returns:
        The UUID as a lower case Python string (``xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxx``)
    """
    _uuid = _uuid.UUIDString()
    if len(_uuid) == 4:
        return "0000{0}-0000-1000-8000-00805f9b34fb".format(_uuid.lower())
    # TODO: Evaluate if this is a necessary method...
    # elif _is_uuid_16bit_compatible(_uuid):
    #    return _uuid[4:8].lower()
    else:
        return _uuid.lower()


def _is_uuid_16bit_compatible(_uuid: str) -> bool:
    test_uuid = "0000ffff-0000-1000-8000-00805f9b34fb"
    test_int = _convert_uuid_to_int(test_uuid)
    uuid_int = _convert_uuid_to_int(_uuid)
    result_int = uuid_int & test_int
    return uuid_int == result_int


def _convert_uuid_to_int(_uuid: str) -> int:
    UUID_cb = CBUUID.alloc().initWithString_(_uuid)
    UUID_data = UUID_cb.data()
    UUID_bytes = UUID_data.getBytes_length_(None, len(UUID_data))
    UUID_int = int.from_bytes(UUID_bytes, byteorder="big")
    return UUID_int


def _convert_int_to_uuid(i: int) -> str:
    UUID_bytes = i.to_bytes(length=16, byteorder="big")
    UUID_data = NSData.alloc().initWithBytes_length_(UUID_bytes, len(UUID_bytes))
    UUID_cb = CBUUID.alloc().initWithData_(UUID_data)
    return UUID_cb.UUIDString().lower()
