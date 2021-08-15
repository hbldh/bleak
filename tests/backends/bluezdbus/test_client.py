from bleak.backends.device import BLEDevice
from dbus_next.constants import MessageType

from dbus_next.message import Message
from bleak.backends.bluezdbus.client import BleakClientBlueZDBus
from bleak.backends.bluezdbus.defs import (
    GATT_CHARACTERISTIC_INTERFACE,
    GATT_DESCRIPTOR_INTERFACE,
    OBJECT_MANAGER_INTERFACE,
    GATT_SERVICE_INTERFACE,
)


MOCK_DEVICE_MAC = "00_11_22_33_44_55"
MOCK_DEVICE_PATH = "/org/bluez/hci0/dev_{}".format(MOCK_DEVICE_MAC)
MOCK_SERVICE_1_HANDLE = 1
MOCK_SERVICE_1_PATH = "{}/service{:04x}".format(MOCK_DEVICE_PATH, MOCK_SERVICE_1_HANDLE)
MOCK_SERVICE_1_UUID = "49789295-e090-452e-8d6c-23899f08119a"
MOCK_SERVICE_1_DATA = {
    "Device": MOCK_DEVICE_PATH,
    "UUID": MOCK_SERVICE_1_UUID,
}


MOCK_CHARACTERISTICS_1_HANDLE = 1
MOCK_CHARACTERISTICS_1_UUID = "ec2db680-c38f-422d-8fa6-6474f556c0ae"
MOCK_CHARACTERISTICS_1_PATH = "{}/char{:04}".format(
    MOCK_SERVICE_1_PATH, MOCK_CHARACTERISTICS_1_HANDLE
)
MOCK_CHARACTERISTICS_1_DATA = {
    "Service": MOCK_SERVICE_1_PATH,
    "Flags": [],
    "UUID": MOCK_CHARACTERISTICS_1_UUID,
}

MOCK_DESCRIPTOR_1_HANDLE = 1
MOCK_DESCRIPTOR_1_UUID = "05fc05d1-4de7-4f5f-a931-806a7fab6db8"
MOCK_DESCRIPTOR_1_PATH = "{}/desc{:04}".format(
    MOCK_CHARACTERISTICS_1_PATH, MOCK_DESCRIPTOR_1_HANDLE
)
MOCK_DESCRIPTOR_1_DATA = {
    "Characteristic": MOCK_CHARACTERISTICS_1_PATH,
    "UUID": MOCK_DESCRIPTOR_1_UUID,
}


def device_message(member, body):
    return Message(
        destination=None,
        path=MOCK_DEVICE_PATH,
        interface=OBJECT_MANAGER_INTERFACE,
        member=member,
        message_type=MessageType.SIGNAL,
        body=body,
    )


def _interfaces_added(path, interface, data):
    return device_message(
        "InterfacesAdded",
        [
            path,
            {interface: data},
        ],
    )


def _interfaces_removed(path, interface):
    return device_message("InterfacesRemoved", [path, [interface]])


def test_remove_service():

    device = BLEDevice(MOCK_DEVICE_MAC, "", details={"path": MOCK_DEVICE_PATH})
    client = BleakClientBlueZDBus(device)

    client._parse_msg(
        _interfaces_added(
            MOCK_SERVICE_1_PATH, GATT_SERVICE_INTERFACE, MOCK_SERVICE_1_DATA
        )
    )
    service_1 = client.services.services.get(MOCK_SERVICE_1_HANDLE)
    assert service_1

    client._parse_msg(
        _interfaces_added(
            MOCK_CHARACTERISTICS_1_PATH,
            GATT_CHARACTERISTIC_INTERFACE,
            MOCK_CHARACTERISTICS_1_DATA,
        )
    )
    characteristics_1 = client.services.characteristics.get(
        MOCK_CHARACTERISTICS_1_HANDLE
    )
    assert characteristics_1
    assert characteristics_1.service_handle == MOCK_SERVICE_1_HANDLE
    assert characteristics_1.service_uuid == MOCK_SERVICE_1_UUID
    assert characteristics_1 in service_1.characteristics

    client._parse_msg(
        _interfaces_added(
            MOCK_DESCRIPTOR_1_PATH,
            GATT_DESCRIPTOR_INTERFACE,
            MOCK_DESCRIPTOR_1_DATA,
        )
    )
    descriptor_1 = client.services.descriptors.get(MOCK_DESCRIPTOR_1_HANDLE)
    assert descriptor_1
    assert descriptor_1.characteristic_handle == MOCK_CHARACTERISTICS_1_HANDLE
    assert descriptor_1.characteristic_uuid == MOCK_CHARACTERISTICS_1_UUID
    assert descriptor_1 in characteristics_1.descriptors

    client._parse_msg(
        _interfaces_removed(MOCK_DESCRIPTOR_1_PATH, GATT_DESCRIPTOR_INTERFACE)
    )
    assert MOCK_DESCRIPTOR_1_HANDLE not in client.services.descriptors
    assert descriptor_1 not in characteristics_1.descriptors

    client._parse_msg(
        _interfaces_removed(MOCK_CHARACTERISTICS_1_PATH, GATT_CHARACTERISTIC_INTERFACE)
    )
    assert MOCK_CHARACTERISTICS_1_HANDLE not in client.services.characteristics
    assert characteristics_1 not in service_1.characteristics

    client._parse_msg(_interfaces_removed(MOCK_SERVICE_1_PATH, GATT_SERVICE_INTERFACE))
    assert MOCK_SERVICE_1_HANDLE not in client.services.services
