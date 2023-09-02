from bleak.uuids import normalize_uuid_16, normalize_uuid_32, normalize_uuid_str


def test_uuid_length_normalization():
    assert normalize_uuid_str("1801") == "00001801-0000-1000-8000-00805f9b34fb"
    assert normalize_uuid_str("DAF51C01") == "daf51c01-0000-1000-8000-00805f9b34fb"


def test_uuid_case_normalization():
    assert (
        normalize_uuid_str("00001801-0000-1000-8000-00805F9B34FB")
        == "00001801-0000-1000-8000-00805f9b34fb"
    )


def test_uuid_16_normalization():
    assert normalize_uuid_16(0x1801) == "00001801-0000-1000-8000-00805f9b34fb"
    assert normalize_uuid_16(0x1) == "00000001-0000-1000-8000-00805f9b34fb"


def test_uuid_32_normalization():
    assert normalize_uuid_32(0x12345678) == "12345678-0000-1000-8000-00805f9b34fb"
    assert normalize_uuid_32(0x1) == "00000001-0000-1000-8000-00805f9b34fb"
