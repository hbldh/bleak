from Foundation import NSData, CBUUID


def cb_uuid_to_str(_uuid: str) -> str:
    if len(_uuid) == 4:
        return "0000{0}-0000-1000-8000-00805f9b34fb".format(_uuid.lower())
    # TODO: Evaluate if this is a necessary method...
    # elif _is_uuid_16bit_compatible(_uuid):
    #    return _uuid[4:8].lower()
    else:
        return _uuid.lower()


def _is_uuid_16bit_compatible(_uuid: str) -> bool:
    test_uuid = "0000FFFF-0000-1000-8000-00805F9B34FB"
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
    return UUID_cb.UUIDString()
