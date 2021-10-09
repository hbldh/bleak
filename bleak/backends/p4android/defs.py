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

SCAN_FAILED_NAMES = {
    ScanCallback.SCAN_FAILED_ALREADY_STARTED: "SCAN_FAILED_ALREADY_STARTED",
    ScanCallback.SCAN_FAILED_APPLICATION_REGISTRATION_FAILED: "SCAN_FAILED_APPLICATION_REGISTRATION_FAILED",
    ScanCallback.SCAN_FAILED_FEATURE_UNSUPPORTED: "SCAN_FAILED_FEATURE_UNSUPPORTED",
    ScanCallback.SCAN_FAILED_INTERNAL_ERROR: "SCAN_FAILED_INTERNAL_ERROR",
}

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

CONNECTION_STATE_NAMES = {
    BluetoothProfile.STATE_DISCONNECTED: "STATE_DISCONNECTED",
    BluetoothProfile.STATE_CONNECTING: "STATE_CONNECTING",
    BluetoothProfile.STATE_CONNECTED: "STATE_CONNECTED",
    BluetoothProfile.STATE_DISCONNECTING: "STATE_DISCONNECTING",
}

CHARACTERISTIC_PROPERTY_DBUS_NAMES = {
    BluetoothGattCharacteristic.PROPERTY_BROADCAST: "broadcast",
    BluetoothGattCharacteristic.PROPERTY_EXTENDED_PROPS: "extended-properties",
    BluetoothGattCharacteristic.PROPERTY_INDICATE: "indicate",
    BluetoothGattCharacteristic.PROPERTY_NOTIFY: "notify",
    BluetoothGattCharacteristic.PROPERTY_READ: "read",
    BluetoothGattCharacteristic.PROPERTY_SIGNED_WRITE: "authenticated-signed-writes",
    BluetoothGattCharacteristic.PROPERTY_WRITE: "write",
    BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE: "write-without-response",
}

CLIENT_CHARACTERISTIC_CONFIGURATION_UUID = "00002902-0000-1000-8000-00805f9b34fb"
