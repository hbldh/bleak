from __future__ import annotations

import enum
import uuid
from typing import Any, Optional, Union


class BleakError(Exception):
    """Base Exception for bleak."""

    pass


class BleakBluetoothNotAvailableReason(enum.Enum):
    """
    Reasons for Bluetooth not being available.

    .. versionadded:: 2.0
    """

    NO_BLUETOOTH = enum.auto()
    """
    The system does not support Bluetooth. I.e. there is no Bluetooth radio.
    """

    NO_BLE_CENTRAL_ROLE = enum.auto()
    """
    The Bluetooth radio does not support the Central role. (E.g. classic-only adapters.)
    """

    POWERED_OFF = enum.auto()
    """
    Bluetooth is not currently available because the radio is turned off.
    """

    DENIED_BY_USER = enum.auto()
    """
    The user denied permission for the app to use Bluetooth when prompted.
    """

    DENIED_BY_SYSTEM = enum.auto()
    """
    Using Bluetooth was denied by the system. E.g. because of a system administrator policy.
    """

    DENIED_BY_UNKNOWN = enum.auto()
    """
    Permission to use Bluetooth was denied for an unknown reason.
    """

    UNKNOWN = enum.auto()
    """
    Bluetooth is not available for an unknown reason.
    """


class BleakBluetoothNotAvailableError(BleakError):
    """
    Exception which is raised if the Bluetooth access is not available for some reason.

    .. versionadded:: 2.0
    """

    def __init__(self, msg: str, reason: BleakBluetoothNotAvailableReason) -> None:
        super().__init__(msg, reason)

    @property
    def reason(self) -> BleakBluetoothNotAvailableReason:
        """
        Gets the reason why Bluetooth is not available.
        """
        return self.args[1]


class BleakCharacteristicNotFoundError(BleakError):
    """
    Exception which is raised if a device does not support a characteristic.

    .. versionadded:: 0.22
    """

    char_specifier: Union[int, str, uuid.UUID]

    def __init__(self, char_specifier: Union[int, str, uuid.UUID]) -> None:
        """
        Args:
            characteristic (str): handle or UUID of the characteristic which was not found
        """
        super().__init__(f"Characteristic {char_specifier} was not found!")
        self.char_specifier = char_specifier


class BleakDeviceNotFoundError(BleakError):
    """
    Exception which is raised if a device can not be found by ``connect``, ``pair`` and ``unpair``.
    This is the case if the OS Bluetooth stack has never seen this device or it was removed and forgotten.

    .. versionadded:: 0.19
    """

    identifier: str

    def __init__(self, identifier: str, *args: object) -> None:
        """
        Args:
            identifier (str): device identifier (Bluetooth address or UUID) of the device which was not found
        """
        super().__init__(*args)
        self.identifier = identifier


class BleakDBusError(BleakError):
    """Specialized exception type for D-Bus errors."""

    def __init__(self, dbus_error: str, error_body: list[Any]):
        """
        Args:
            dbus_error (str): The D-Bus error, e.g. ``org.freedesktop.DBus.Error.UnknownObject``.
            error_body (list): Body of the D-Bus error, sometimes containing error description or details.
        """
        super().__init__(dbus_error, *error_body)

    @property
    def dbus_error(self) -> str:
        """Gets the D-Bus error name, e.g. ``org.freedesktop.DBus.Error.UnknownObject``."""
        return self.args[0]

    @property
    def dbus_error_details(self) -> Optional[str]:
        """Gets the optional D-Bus error details, e.g. 'Invalid UUID'."""
        if len(self.args) > 1:
            details = self.args[1]
            # Some error descriptions can be further parsed to be even more helpful
            if "ATT error: 0x" in details:
                more_detail = PROTOCOL_ERROR_CODES.get(
                    int(details.rsplit("x")[1], 16), "Unknown code"
                )
                details += f" ({more_detail})"
            return details
        return None

    def __str__(self) -> str:
        name = f"[{self.dbus_error}]"
        details = self.dbus_error_details
        return (name + " " + details) if details else name


CONTROLLER_ERROR_CODES = {
    0x00: "Success",
    0x01: "Unknown HCI Command",
    0x02: "Unknown Connection Identifier",
    0x03: "Hardware Failure",
    0x04: "Page Timeout",
    0x05: "Authentication Failure",
    0x06: "PIN or Key Missing",
    0x07: "Memory Capacity Exceeded",
    0x08: "Connection Timeout",
    0x09: "Connection Limit Exceeded",
    0x0A: "Synchronous Connection Limit To A Device Exceeded",
    0x0B: "Connection Already Exists",
    0x0C: "Command Disallowed",
    0x0D: "Connection Rejected due to Limited Resources",
    0x0E: "Connection Rejected Due To Security Reasons",
    0x0F: "Connection Rejected due to Unacceptable BD_ADDR",
    0x10: "Connection Accept Timeout Exceeded",
    0x11: "Unsupported Feature or Parameter Value",
    0x12: "Invalid HCI Command Parameters",
    0x13: "Remote User Terminated Connection",
    0x14: "Remote Device Terminated Connection due to Low Resources",
    0x15: "Remote Device Terminated Connection due to Power Off",
    0x16: "Connection Terminated By Local Host",
    0x17: "Repeated Attempts",
    0x18: "Pairing Not Allowed",
    0x19: "Unknown LMP PDU",
    0x1A: "Unsupported Remote Feature / Unsupported LMP Feature",
    0x1B: "SCO Offset Rejected",
    0x1C: "SCO Interval Rejected",
    0x1D: "SCO Air Mode Rejected",
    0x1E: "Invalid LMP Parameters / Invalid LL Parameters",
    0x1F: "Unspecified Error",
    0x20: "Unsupported LMP Parameter Value / Unsupported LL Parameter Value",
    0x21: "Role Change Not Allowed",
    0x22: "LMP Response Timeout / LL Response Timeout",
    0x23: "LMP Error Transaction Collision / LL Procedure Collision",
    0x24: "LMP PDU Not Allowed",
    0x25: "Encryption Mode Not Acceptable",
    0x26: "Link Key cannot be Changed",
    0x27: "Requested QoS Not Supported",
    0x28: "Instant Passed",
    0x29: "Pairing With Unit Key Not Supported",
    0x2A: "Different Transaction Collision",
    0x2B: "Reserved for future use",
    0x2C: "QoS Unacceptable Parameter",
    0x2D: "QoS Rejected",
    0x2E: "Channel Classification Not Supported",
    0x2F: "Insufficient Security",
    0x30: "Parameter Out Of Mandatory Range",
    0x31: "Reserved for future use",
    0x32: "Role Switch Pending",
    0x33: "Reserved for future use",
    0x34: "Reserved Slot Violation",
    0x35: "Role Switch Failed",
    0x36: "Extended Inquiry Response Too Large",
    0x37: "Secure Simple Pairing Not Supported By Host",
    0x38: "Host Busy - Pairing",
    0x39: "Connection Rejected due to No Suitable Channel Found",
    0x3A: "Controller Busy",
    0x3B: "Unacceptable Connection Parameters",
    0x3C: "Advertising Timeout",
    0x3D: "Connection Terminated due to MIC Failure",
    0x3E: "Connection Failed to be Established / Synchronization Timeout",
    0x3F: "MAC Connection Failed",
    0x40: "Coarse Clock Adjustment Rejected but Will Try to Adjust Using Clock",
    0x41: "Type0 Submap Not Defined",
    0x42: "Unknown Advertising Identifier",
    0x43: "Limit Reached",
    0x44: "Operation Cancelled by Host",
    0x45: "Packet Too Long",
}

# as defined in Bluetooth Core Specification v5.2, volume 3, part F, section 3.4.1.1, table 3.4.
PROTOCOL_ERROR_CODES = {
    0x01: "Invalid Handle",
    0x02: "Read Not Permitted",
    0x03: "Write Not Permitted",
    0x04: "Invalid PDU",
    0x05: "Insufficient Authentication",
    0x06: "Request Not Supported",
    0x07: "Invalid Offset",
    0x08: "Insufficient Authorization",
    0x09: "Prepare Queue Full",
    0x0A: "Attribute Not Found",
    0x0B: "Attribute Not Long",
    0x0C: "Insufficient Encryption Key Size",
    0x0D: "Invalid Attribute Value Length",
    0x0E: "Unlikely Error",
    0x0F: "Insufficient Encryption",
    0x10: "Unsupported Group Type",
    0x11: "Insufficient Resource",
    0x12: "Database Out Of Sync",
    0x13: "Value Not Allowed",
    0x80: "Application-specific Error 0x80",
    0x81: "Application-specific Error 0x81",
    0x82: "Application-specific Error 0x82",
    0x83: "Application-specific Error 0x83",
    0x84: "Application-specific Error 0x84",
    0x85: "Application-specific Error 0x85",
    0x86: "Application-specific Error 0x86",
    0x87: "Application-specific Error 0x87",
    0x88: "Application-specific Error 0x88",
    0x89: "Application-specific Error 0x89",
    0x8A: "Application-specific Error 0x8A",
    0x8B: "Application-specific Error 0x8B",
    0x8C: "Application-specific Error 0x8C",
    0x8D: "Application-specific Error 0x8D",
    0x8E: "Application-specific Error 0x8E",
    0x8F: "Application-specific Error 0x8F",
    0x90: "Application-specific Error 0x90",
    0x91: "Application-specific Error 0x91",
    0x92: "Application-specific Error 0x92",
    0x93: "Application-specific Error 0x93",
    0x94: "Application-specific Error 0x94",
    0x95: "Application-specific Error 0x95",
    0x96: "Application-specific Error 0x96",
    0x97: "Application-specific Error 0x97",
    0x98: "Application-specific Error 0x98",
    0x99: "Application-specific Error 0x99",
    0x9A: "Application-specific Error 0x9A",
    0x9B: "Application-specific Error 0x9B",
    0x9C: "Application-specific Error 0x9C",
    0x9D: "Application-specific Error 0x9D",
    0x9E: "Application-specific Error 0x9E",
    0x9F: "Application-specific Error 0x9F",
    0xFC: "Write Request Rejected",
    0xFD: "Client Characteristic Configuration Descriptor Improperly Configured",
    0xFE: "Procedure Already in Progress",
    0xFF: "Out of Range",
}


class BleakGATTProtocolErrorCode(enum.IntEnum):
    """
    Enumeration of GATT protocol error codes.

    .. versionadded:: 3.0
    """

    INVALID_HANDLE = 0x01
    READ_NOT_PERMITTED = 0x02
    WRITE_NOT_PERMITTED = 0x03
    INVALID_PDU = 0x04
    INSUFFICIENT_AUTHENTICATION = 0x05
    REQUEST_NOT_SUPPORTED = 0x06
    INVALID_OFFSET = 0x07
    INSUFFICIENT_AUTHORIZATION = 0x08
    PREPARE_QUEUE_FULL = 0x09
    ATTRIBUTE_NOT_FOUND = 0x0A
    ATTRIBUTE_NOT_LONG = 0x0B
    INSUFFICIENT_ENCRYPTION_KEY_SIZE = 0x0C
    INVALID_ATTRIBUTE_VALUE_LENGTH = 0x0D
    UNLIKELY_ERROR = 0x0E
    INSUFFICIENT_ENCRYPTION = 0x0F
    UNSUPPORTED_GROUP_TYPE = 0x10
    INSUFFICIENT_RESOURCE = 0x11
    DATABASE_OUT_OF_SYNC = 0x12
    VALUE_NOT_ALLOWED = 0x13
    WRITE_REQUEST_REJECTED = 0xFC
    CCCD_IMPROPERLY_CONFIGURED = 0xFD
    PROCEDURE_ALREADY_IN_PROGRESS = 0xFE
    OUT_OF_RANGE = 0xFF

    @classmethod
    def _missing_(cls, value: Any) -> BleakGATTProtocolErrorCode | None:
        try:
            obj = int.__new__(cls, value)
        except TypeError:  # pragma: no cover
            return None

        obj._value_ = value
        obj._name_ = f"{cls.__name__}[{value}]"
        return obj


class BleakGATTProtocolError(BleakError):
    """
    Exception which is raised if a GATT protocol error occurs.

    .. versionadded:: 3.0
    """

    def __init__(self, error_code: int) -> None:
        """
        Args:
            error_code (int): The GATT protocol error code.
        """
        error_message = PROTOCOL_ERROR_CODES.get(error_code, "Unknown code")
        super().__init__(error_code, f"GATT Protocol Error: {error_message}")

    @property
    def code(self) -> BleakGATTProtocolErrorCode:
        """
        Gets the GATT protocol error code.
        """
        return BleakGATTProtocolErrorCode(self.args[0])
