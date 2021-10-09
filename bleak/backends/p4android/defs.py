# -*- coding: utf-8 -*-

import bleak.exc
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
GATT_STATUS_STRINGS = {
    # https://developer.android.com/reference/android/bluetooth/BluetoothGatt
    # https://android.googlesource.com/platform/external/bluetooth/bluedroid/+/5738f83aeb59361a0a2eda2460113f6dc9194271/stack/include/gatt_api.h
    # https://android.googlesource.com/platform/system/bt/+/master/stack/include/gatt_api.h
    # https://www.bluetooth.com/specifications/bluetooth-core-specification/
    **bleak.exc.CONTROLLER_ERROR_CODES,
    **bleak.exc.PROTOCOL_ERROR_CODES,
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

PROPERTY_BROADCAST = BluetoothGattCharacteristic.PROPERTY_BROADCAST
PROPERTY_EXTENDED_PROPS = BluetoothGattCharacteristic.PROPERTY_EXTENDED_PROPS
PROPERTY_INDICATE = BluetoothGattCharacteristic.PROPERTY_INDICATE
PROPERTY_NOTIFY = BluetoothGattCharacteristic.PROPERTY_NOTIFY
PROPERTY_READ = BluetoothGattCharacteristic.PROPERTY_READ
PROPERTY_SIGNED_WRITE = BluetoothGattCharacteristic.PROPERTY_SIGNED_WRITE
PROPERTY_WRITE = BluetoothGattCharacteristic.PROPERTY_WRITE
PROPERTY_WRITE_NO_RESPONSE = BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE
CHARACTERISTIC_PROPERTY_DBUS_NAMES = {
    PROPERTY_BROADCAST: "broadcast",
    PROPERTY_EXTENDED_PROPS: "extended-properties",
    PROPERTY_INDICATE: "indicate",
    PROPERTY_NOTIFY: "notify",
    PROPERTY_READ: "read",
    PROPERTY_SIGNED_WRITE: "authenticated-signed-writes",
    PROPERTY_WRITE: "write",
    PROPERTY_WRITE_NO_RESPONSE: "write-without-response",
}

CLIENT_CHARACTERISTIC_CONFIGURATION_UUID = "00002902-0000-1000-8000-00805f9b34fb"
