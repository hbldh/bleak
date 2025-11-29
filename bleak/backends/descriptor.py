# Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>
"""
Interface class for the Bleak representation of a GATT Descriptor
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bleak.uuids import normalize_uuid_16

# avoid circular import
if TYPE_CHECKING:
    from bleak.backends.characteristic import BleakGATTCharacteristic


_descriptor_descriptions = {
    normalize_uuid_16(0x2905): [
        "Characteristic Aggregate Format",
        "org.bluetooth.descriptor.gatt.characteristic_aggregate_format",
        "0x2905",
        "GSS",
    ],
    normalize_uuid_16(0x2900): [
        "Characteristic Extended Properties",
        "org.bluetooth.descriptor.gatt.characteristic_extended_properties",
        "0x2900",
        "GSS",
    ],
    normalize_uuid_16(0x2904): [
        "Characteristic Presentation Format",
        "org.bluetooth.descriptor.gatt.characteristic_presentation_format",
        "0x2904",
        "GSS",
    ],
    normalize_uuid_16(0x2901): [
        "Characteristic User Description",
        "org.bluetooth.descriptor.gatt.characteristic_user_description",
        "0x2901",
        "GSS",
    ],
    normalize_uuid_16(0x2902): [
        "Client Characteristic Configuration",
        "org.bluetooth.descriptor.gatt.client_characteristic_configuration",
        "0x2902",
        "GSS",
    ],
    normalize_uuid_16(0x290B): [
        "Environmental Sensing Configuration",
        "org.bluetooth.descriptor.es_configuration",
        "0x290B",
        "GSS",
    ],
    normalize_uuid_16(0x290C): [
        "Environmental Sensing Measurement",
        "org.bluetooth.descriptor.es_measurement",
        "0x290C",
        "GSS",
    ],
    normalize_uuid_16(0x290D): [
        "Environmental Sensing Trigger Setting",
        "org.bluetooth.descriptor.es_trigger_setting",
        "0x290D",
        "GSS",
    ],
    normalize_uuid_16(0x2907): [
        "External Report Reference",
        "org.bluetooth.descriptor.external_report_reference",
        "0x2907",
        "GSS",
    ],
    normalize_uuid_16(0x2909): [
        "Number of Digitals",
        "org.bluetooth.descriptor.number_of_digitals",
        "0x2909",
        "GSS",
    ],
    normalize_uuid_16(0x2908): [
        "Report Reference",
        "org.bluetooth.descriptor.report_reference",
        "0x2908",
        "GSS",
    ],
    normalize_uuid_16(0x2903): [
        "Server Characteristic Configuration",
        "org.bluetooth.descriptor.gatt.server_characteristic_configuration",
        "0x2903",
        "GSS",
    ],
    normalize_uuid_16(0x290E): [
        "Time Trigger Setting",
        "org.bluetooth.descriptor.time_trigger_setting",
        "0x290E",
        "GSS",
    ],
    normalize_uuid_16(0x2906): [
        "Valid Range",
        "org.bluetooth.descriptor.valid_range",
        "0x2906",
        "GSS",
    ],
    normalize_uuid_16(0x290A): [
        "Value Trigger Setting",
        "org.bluetooth.descriptor.value_trigger_setting",
        "0x290A",
        "GSS",
    ],
}


class BleakGATTDescriptor:
    """The Bleak representation of a GATT Descriptor"""

    def __init__(
        self, obj: Any, handle: int, uuid: str, characteristic: BleakGATTCharacteristic
    ):
        """
        Args:
            obj: The backend-specific object for the descriptor.
            handle: The handle of the descriptor.
            uuid: The UUID of the descriptor.
            characteristic: The characteristic that this descriptor belongs to.
        """
        self.obj = obj
        self._handle = handle
        self._uuid = uuid
        self._characteristic = characteristic

    def __str__(self):
        return f"{self.uuid} (Handle: {self.handle}): {self.description}"

    @property
    def characteristic_uuid(self) -> str:
        """UUID for the characteristic that this descriptor belongs to"""
        return self._characteristic.uuid

    @property
    def characteristic_handle(self) -> int:
        """handle for the characteristic that this descriptor belongs to"""
        return self._characteristic.handle

    @property
    def uuid(self) -> str:
        """UUID for this descriptor"""
        return self._uuid

    @property
    def handle(self) -> int:
        """Integer handle for this descriptor"""
        return self._handle

    @property
    def description(self) -> str:
        """A text description of what this descriptor represents"""
        return _descriptor_descriptions.get(self.uuid, ["Unknown"])[0]
