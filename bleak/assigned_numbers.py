"""
Bluetooth Assigned Numbers
--------------------------

This module contains useful assigned numbers from the Bluetooth spec.

See <https://www.bluetooth.com/specifications/assigned-numbers/>.
"""


from enum import IntEnum


class AdvertisementDataType(IntEnum):
    """
    Generic Access Profile advertisement data types.

    `Source <https://btprodspecificationrefs.blob.core.windows.net/assigned-numbers/Assigned%20Number%20Types/Generic%20Access%20Profile.pdf>`.

    .. versionadded:: 0.15.0
    """

    FLAGS = 0x01
    INCOMPLETE_LIST_SERVICE_UUID16 = 0x02
    COMPLETE_LIST_SERVICE_UUID16 = 0x03
    INCOMPLETE_LIST_SERVICE_UUID32 = 0x04
    COMPLETE_LIST_SERVICE_UUID32 = 0x05
    INCOMPLETE_LIST_SERVICE_UUID128 = 0x06
    COMPLETE_LIST_SERVICE_UUID128 = 0x07
    SHORTENED_LOCAL_NAME = 0x08
    COMPLETE_LOCAL_NAME = 0x09
    TX_POWER_LEVEL = 0x0A
    CLASS_OF_DEVICE = 0x0D

    SERVICE_DATA_UUID16 = 0x16
    SERVICE_DATA_UUID32 = 0x20
    SERVICE_DATA_UUID128 = 0x21

    MANUFACTURER_SPECIFIC_DATA = 0xFF


AppearanceCategories = {
    0x000: "Unknown",
    0x001: "Phone",
    0x002: "Computer",
    0x003: "Watch",
    0x004: "Clock",
    0x005: "Display",
    0x006: "Remote Control",
    0x007: "Eye-glasses",
    0x008: "Tag",
    0x009: "Keyring",
    0x00A: "Media Player",
    0x00B: "Barcode Scanner",
    0x00C: "Thermometer",
    0x00D: "Heart Rate Sensor",
    0x00E: "Blood Pressure",
    0x00F: "Human Interface Device",
    0x010: "Glucose Meter",
    0x011: "Running Walking Sensor",
    0x012: "Cycling",
    0x013: "Control Device",
    0x014: "Network Device",
    0x015: "Sensor",
    0x016: "Light Fixtures",
    0x017: "Fan",
    0x018: "HVAC",
    0x019: "Air Conditioning",
    0x01A: "Humidifier",
    0x01B: "Heating",
    0x01C: "Access Control",
    0x01D: "Motorized Device",
    0x01E: "Power Device",
    0x01F: "Light Source",
    0x020: "Window Covering",
    0x021: "Audio Sink",
    0x022: "Audio Source",
    0x023: "Motorized Vehicle",
    0x024: "Domestic Appliance",
    0x025: "Wearable Audio Device",
    0x026: "Aircraft",
    0x027: "AV Equipment",
    0x028: "Display Equipment",
    0x029: "Hearing aid",
    0x02A: "Gaming",
    0x02B: "Signage",
    0x031: "Pulse Oximeter",
    0x032: "Weight Scale",
    0x033: "Personal Mobility Device",
    0x034: "Continuous Glucose Monitor",
    0x035: "Insulin Pump",
    0x036: "Medication Delivery",
    0x051: "Outdoor Sports Activity",
}
