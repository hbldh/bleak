# -*- coding: utf-8 -*-
"""
Interface class for the Bleak representation of a GATT Descriptor

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
from typing import Any

_descriptor_descriptions = {
    "00002905-0000-1000-8000-00805f9b34fb": [
        "Characteristic Aggregate Format",
        "org.bluetooth.descriptor.gatt.characteristic_aggregate_format",
        "0x2905",
        "GSS",
    ],
    "00002900-0000-1000-8000-00805f9b34fb": [
        "Characteristic Extended Properties",
        "org.bluetooth.descriptor.gatt.characteristic_extended_properties",
        "0x2900",
        "GSS",
    ],
    "00002904-0000-1000-8000-00805f9b34fb": [
        "Characteristic Presentation Format",
        "org.bluetooth.descriptor.gatt.characteristic_presentation_format",
        "0x2904",
        "GSS",
    ],
    "00002901-0000-1000-8000-00805f9b34fb": [
        "Characteristic User Description",
        "org.bluetooth.descriptor.gatt.characteristic_user_description",
        "0x2901",
        "GSS",
    ],
    "00002902-0000-1000-8000-00805f9b34fb": [
        "Client Characteristic Configuration",
        "org.bluetooth.descriptor.gatt.client_characteristic_configuration",
        "0x2902",
        "GSS",
    ],
    "0000290b-0000-1000-8000-00805f9b34fb": [
        "Environmental Sensing Configuration",
        "org.bluetooth.descriptor.es_configuration",
        "0x290B",
        "GSS",
    ],
    "0000290c-0000-1000-8000-00805f9b34fb": [
        "Environmental Sensing Measurement",
        "org.bluetooth.descriptor.es_measurement",
        "0x290C",
        "GSS",
    ],
    "0000290d-0000-1000-8000-00805f9b34fb": [
        "Environmental Sensing Trigger Setting",
        "org.bluetooth.descriptor.es_trigger_setting",
        "0x290D",
        "GSS",
    ],
    "00002907-0000-1000-8000-00805f9b34fb": [
        "External Report Reference",
        "org.bluetooth.descriptor.external_report_reference",
        "0x2907",
        "GSS",
    ],
    "00002909-0000-1000-8000-00805f9b34fb": [
        "Number of Digitals",
        "org.bluetooth.descriptor.number_of_digitals",
        "0x2909",
        "GSS",
    ],
    "00002908-0000-1000-8000-00805f9b34fb": [
        "Report Reference",
        "org.bluetooth.descriptor.report_reference",
        "0x2908",
        "GSS",
    ],
    "00002903-0000-1000-8000-00805f9b34fb": [
        "Server Characteristic Configuration",
        "org.bluetooth.descriptor.gatt.server_characteristic_configuration",
        "0x2903",
        "GSS",
    ],
    "0000290e-0000-1000-8000-00805f9b34fb": [
        "Time Trigger Setting",
        "org.bluetooth.descriptor.time_trigger_setting",
        "0x290E",
        "GSS",
    ],
    "00002906-0000-1000-8000-00805f9b34fb": [
        "Valid Range",
        "org.bluetooth.descriptor.valid_range",
        "0x2906",
        "GSS",
    ],
    "0000290a-0000-1000-8000-00805f9b34fb": [
        "Value Trigger Setting",
        "org.bluetooth.descriptor.value_trigger_setting",
        "0x290A",
        "GSS",
    ],
}


class BleakGATTDescriptor(abc.ABC):
    """Interface for the Bleak representation of a GATT Descriptor"""

    def __init__(self, obj: Any):
        self.obj = obj

    def __str__(self):
        return f"{self.uuid} (Handle: {self.handle}): {self.description}"

    @property
    @abc.abstractmethod
    def characteristic_uuid(self) -> str:
        """UUID for the characteristic that this descriptor belongs to"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def characteristic_handle(self) -> int:
        """handle for the characteristic that this descriptor belongs to"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def uuid(self) -> str:
        """UUID for this descriptor"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def handle(self) -> int:
        """Integer handle for this descriptor"""
        raise NotImplementedError()

    @property
    def description(self) -> str:
        """A text description of what this descriptor represents"""
        return _descriptor_descriptions.get(self.uuid.lower(), ["None"])[0]
