# -*- coding: utf-8 -*-

from android.permissions import Permission
from jnius import autoclass, cast

# caching constants avoids unneccessary extra use of the jni-python interface, which can be slow

List = autoclass("java.util.ArrayList")
BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
ScanCallback = autoclass("android.bluetooth.le.ScanCallback")
ScanFilter = autoclass("android.bluetooth.le.ScanFilter")
ScanFilterBuilder = autoclass("android.bluetooth.le.ScanFilter$Builder")
ScanSettings = autoclass("android.bluetooth.le.ScanSettings")
ScanSettingsBuilder = autoclass("android.bluetooth.le.ScanSettings$Builder")
BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")
BluetoothGatt = autoclass("android.bluetooth.BluetoothGatt")
BluetoothGattCharacteristic = autoclass("android.bluetooth.BluetoothGattCharacteristic")
BluetoothGattDescriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
BluetoothProfile = autoclass("android.bluetooth.BluetoothProfile")
PythonActivity = autoclass("org.kivy.android.PythonActivity")
activity = cast("android.app.Activity", PythonActivity.mActivity)
context = cast("android.content.Context", activity.getApplicationContext())

BLEAK_JNI_NAMESPACE = "com.github.hbldh.bleak"
PythonScanCallback = autoclass(BLEAK_JNI_NAMESPACE + ".PythonScanCallback")
PythonBluetoothGattCallback = autoclass(
    BLEAK_JNI_NAMESPACE + ".PythonBluetoothGattCallback"
)

ACCESS_FINE_LOCATION = Permission.ACCESS_FINE_LOCATION
ACCESS_COARSE_LOCATION = Permission.ACCESS_COARSE_LOCATION
ACCESS_BACKGROUND_LOCATION = "android.permission.ACCESS_BACKGROUND_LOCATION"

ACTION_STATE_CHANGED = BluetoothAdapter.ACTION_STATE_CHANGED
EXTRA_STATE = BluetoothAdapter.EXTRA_STATE

STATE_ERROR = BluetoothAdapter.ERROR
STATE_OFF = BluetoothAdapter.STATE_OFF
STATE_TURNING_ON = BluetoothAdapter.STATE_TURNING_ON
STATE_ON = BluetoothAdapter.STATE_ON
STATE_TURNING_OFF = BluetoothAdapter.STATE_TURNING_OFF

SCAN_FAILED_ALREADY_STARTED = ScanCallback.SCAN_FAILED_ALREADY_STARTED
SCAN_FAILED_APPLICATION_REGISTRATION_FAILED = (
    ScanCallback.SCAN_FAILED_APPLICATION_REGISTRATION_FAILED
)
SCAN_FAILED_FEATURE_UNSUPPORTED = ScanCallback.SCAN_FAILED_FEATURE_UNSUPPORTED
SCAN_FAILED_INTERNAL_ERROR = ScanCallback.SCAN_FAILED_INTERNAL_ERROR
SCAN_FAILED_NAMES = {
    SCAN_FAILED_ALREADY_STARTED: "SCAN_FAILED_ALREADY_STARTED",
    SCAN_FAILED_APPLICATION_REGISTRATION_FAILED: "SCAN_FAILED_APPLICATION_REGISTRATION_FAILED",
    SCAN_FAILED_FEATURE_UNSUPPORTED: "SCAN_FAILED_FEATURE_UNSUPPORTED",
    SCAN_FAILED_INTERNAL_ERROR: "SCAN_FAILED_INTERNAL_ERROR",
}

TRANSPORT_AUTO = BluetoothDevice.TRANSPORT_AUTO
TRANSPORT_BREDR = BluetoothDevice.TRANSPORT_BREDR
TRANSPORT_LE = BluetoothDevice.TRANSPORT_LE
ACTION_BOND_STATE_CHANGED = BluetoothDevice.ACTION_BOND_STATE_CHANGED
EXTRA_BOND_STATE = BluetoothDevice.EXTRA_BOND_STATE
BOND_BONDED = BluetoothDevice.BOND_BONDED
BOND_BONDING = BluetoothDevice.BOND_BONDING
BOND_NONE = BluetoothDevice.BOND_NONE
GATT_SUCCESS = BluetoothGatt.GATT_SUCCESS
WRITE_TYPE_NO_RESPONSE = BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
WRITE_TYPE_DEFAULT = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
WRITE_TYPE_SIGNED = BluetoothGattCharacteristic.WRITE_TYPE_SIGNED
DISABLE_NOTIFICATION_VALUE = BluetoothGattDescriptor.DISABLE_NOTIFICATION_VALUE
ENABLE_NOTIFICATION_VALUE = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
ENABLE_INDICATION_VALUE = BluetoothGattDescriptor.ENABLE_INDICATION_VALUE

GATT_SUCCESS = 0x0000
GATT_STATUS_NAMES = {
    # https://developer.android.com/reference/android/bluetooth/BluetoothGatt
    # https://android.googlesource.com/platform/external/bluetooth/bluedroid/+/5738f83aeb59361a0a2eda2460113f6dc9194271/stack/include/gatt_api.h
    # https://android.googlesource.com/platform/system/bt/+/master/stack/include/gatt_api.h
    # https://www.bluetooth.com/specifications/bluetooth-core-specification/
    # if error codes are missing you could check the bluetooth
    # specification (last link above) as not all were copied over, since
    # android repurposed so many
    0x0000: "GATT_SUCCESS",
    0x0001: "GATT_INVALID_HANDLE",
    0x0002: "GATT_READ_NOT_PERMIT",
    0x0003: "GATT_WRITE_NOT_PERMIT",
    0x0004: "GATT_INVALID_PDU",
    0x0005: "GATT_INSUF_AUTHENTICATION",
    0x0006: "GATT_REQ_NOT_SUPPORTED",
    0x0007: "GATT_INVALID_OFFSET",
    0x0008: "GATT_INSUF_AUTHORIZATION",
    0x0009: "GATT_PREPARE_Q_FULL",
    0x000A: "GATT_NOT_FOUND",
    0x000B: "GATT_NOT_LONG",
    0x000C: "GATT_INSUF_KEY_SIZE",
    0x000D: "GATT_INVALID_ATTR_LEN",
    0x000E: "GATT_ERR_UNLIKELY",
    0x000F: "GATT_INSUF_ENCRYPTION",
    0x0010: "GATT_UNSUPPORT_GRP_TYPE",
    0x0011: "GATT_INSUF_RESOURCE",
    0x0012: "GATT_DATABASE_OUT_OF_SYNC",
    0x0013: "GATT_VALUE_NOT_ALLOWED",
    0x0014: "BLU_REM_TERM_CONN_LOW_RES",  # names made up from bluetooth spec
    0x0015: "BLU_REM_TERM_CONN_POW_OFF",
    0x0016: "BLU_LOC_TERM_CONN",
    0x0017: "BLU_REPEATED_ATTEMPTS",
    0x0018: "BLU_PAIRING_NOT_ALLOWED",
    0x007F: "GATT_TOO_SHORT",
    0x0080: "GATT_NO_RESOURCES",
    0x0081: "GATT_INTERNAL_ERROR",
    0x0082: "GATT_WRONG_STATE",
    0x0083: "GATT_DB_FULL",
    0x0084: "GATT_BUSY",
    0x0085: "GATT_ERROR",
    0x0086: "GATT_CMD_STARTED",
    0x0087: "GATT_ILLEGAL_PARAMETER",
    0x0088: "GATT_PENDING",
    0x0089: "GATT_AUTH_FAIL",
    0x008A: "GATT_MORE",
    0x008B: "GATT_INVALID_CFG",
    0x008C: "GATT_SERVICE_STARTED",
    0x008D: "GATT_ENCRYPED_NO_MITM",
    0x008E: "GATT_NOT_ENCRYPTED",
    0x008F: "GATT_CONGESTED",
    0x0090: "GATT_DUP_REG",
    0x0091: "GATT_ALREADY_OPEN",
    0x0092: "GATT_CANCEL",
    0x00FD: "GATT_CCC_CFG_ERR",
    0x00FE: "GATT_PRC_IN_PROGRESS",
    0x00FF: "GATT_OUT_OF_RANGE",
    0x0101: "GATT_FAILURE",
}

STATE_DISCONNECTED = BluetoothProfile.STATE_DISCONNECTED
STATE_CONNECTING = BluetoothProfile.STATE_CONNECTING
STATE_CONNECTED = BluetoothProfile.STATE_CONNECTED
STATE_DISCONNECTING = BluetoothProfile.STATE_DISCONNECTING
CONNECTION_STATE_NAMES = {
    STATE_DISCONNECTED: "STATE_DISCONNECTED",
    STATE_CONNECTING: "STATE_CONNECTING",
    STATE_CONNECTED: "STATE_CONNECTED",
    STATE_DISCONNECTING: "STATE_DISCONNECTING",
}
