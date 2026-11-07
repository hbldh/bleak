import enum


class ScanFailed(enum.IntEnum):
    ALREADY_STARTED = 0x00000001
    APPLICATION_REGISTRATION_FAILED = 0x00000002
    FEATURE_UNSUPPORTED = 0x00000004
    INTERNAL_ERROR = 0x00000003
    SCAN_FAILED_OUT_OF_HARDWARE_RESOURCES = 0x00000005
    SCAN_FAILED_SCANNING_TOO_FREQUENTLY = 0x00000006


GATT_SUCCESS = 0x0000
# # TODO: we may need different lookups, e.g. one for bleak.exc.CONTROLLER_ERROR_CODES
# GATT_STATUS_STRINGS = {
#     # https://developer.android.com/reference/android/bluetooth/BluetoothGatt
#     # https://android.googlesource.com/platform/external/bluetooth/bluedroid/+/5738f83aeb59361a0a2eda2460113f6dc9194271/stack/include/gatt_api.h
#     # https://android.googlesource.com/platform/system/bt/+/master/stack/include/gatt_api.h
#     # https://www.bluetooth.com/specifications/bluetooth-core-specification/
#     **PROTOCOL_ERROR_CODES,
#     0x007F: "Too Short",
#     0x0080: "No Resources",
#     0x0081: "Internal Error",
#     0x0082: "Wrong State",
#     0x0083: "DB Full",
#     0x0084: "Busy",
#     0x0085: "Error",
#     0x0086: "Command Started",
#     0x0087: "Illegal Parameter",
#     0x0088: "Pending",
#     0x0089: "Auth Failure",
#     0x008A: "More",
#     0x008B: "Invalid Configuration",
#     0x008C: "Service Started",
#     0x008D: "Encrypted No MITM",
#     0x008E: "Not Encrypted",
#     0x008F: "Congested",
#     0x0090: "Duplicate Reg",
#     0x0091: "Already Open",
#     0x0092: "Cancel",
#     0x0101: "Failure",
# }
