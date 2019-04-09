# -*- coding: utf-8 -*-
"""
Interface class for the Bleak representation of a GATT Descriptor

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
from typing import Any


_ = """Characteristic Aggregate Format	org.bluetooth.descriptor.gatt.characteristic_aggregate_format	0x2905	GSS
Characteristic Extended Properties	org.bluetooth.descriptor.gatt.characteristic_extended_properties	0x2900	GSS
Characteristic Presentation Format	org.bluetooth.descriptor.gatt.characteristic_presentation_format	0x2904	GSS
Characteristic User Description	org.bluetooth.descriptor.gatt.characteristic_user_description	0x2901	GSS
Client Characteristic Configuration	org.bluetooth.descriptor.gatt.client_characteristic_configuration	0x2902	GSS
Environmental Sensing Configuration	org.bluetooth.descriptor.es_configuration	0x290B	GSS
Environmental Sensing Measurement	org.bluetooth.descriptor.es_measurement	0x290C	GSS
Environmental Sensing Trigger Setting	org.bluetooth.descriptor.es_trigger_setting	0x290D	GSS
External Report Reference	org.bluetooth.descriptor.external_report_reference	0x2907	GSS
Number of Digitals	org.bluetooth.descriptor.number_of_digitals	0x2909	GSS
Report Reference	org.bluetooth.descriptor.report_reference	0x2908	GSS
Server Characteristic Configuration	org.bluetooth.descriptor.gatt.server_characteristic_configuration	0x2903	GSS
Time Trigger Setting	org.bluetooth.descriptor.time_trigger_setting	0x290E	GSS
Valid Range	org.bluetooth.descriptor.valid_range	0x2906	GSS
Value Trigger Setting	org.bluetooth.descriptor.value_trigger_setting	0x290A	GSS
"""
_descriptor_descriptions = {
    "0000{0}-0000-1000-8000-00805f9b34fb".format(v[2][2:]): v
    for v in [x.split("\t") for x in _.splitlines()]
}


class BleakGATTDescriptor(abc.ABC):
    """Interface for the Bleak representation of a GATT Descriptor"""

    def __init__(self, obj: Any):
        self.obj = obj

    def __str__(self):
        return "{0}: {1}".format(self.uuid, self.description)

    @property
    @abc.abstractmethod
    def characteristic_uuid(self) -> str:
        """UUID for the characteristic that this descriptor belongs to"""
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
    def description(self):
        """A text description of what this descriptor represents"""
        return _descriptor_descriptions.get(self.uuid, ["None"])[0]
