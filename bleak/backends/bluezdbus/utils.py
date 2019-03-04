# -*- coding: utf-8 -*-
import re

from bleak.uuids import uuidstr_to_str

from bleak.backends.bluezdbus import defs
from bleak.exc import BleakError

_mac_address_regex = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
_hci_device_regex = re.compile("^hci(\d+)$")


def validate_mac_address(address):
    return _mac_address_regex.match(address) is not None


def validate_hci_device(hci_device):
    return _hci_device_regex.match(hci_device) is not None


def get_device_object_path(hci_device, address):
    """Get object path for a Bluetooth device.

    Service         org.bluez
    Interface       org.bluez.Device1
    Object path     [variable prefix]/{hci0,hci1,...}/dev_XX_XX_XX_XX_XX_XX

    Args:
        hci_device (str): Which bluetooth adapter to connect with.
        address (str): The MAC adress of the bluetooth device.

    Returns:
        String representation of device object path on format
        `/org/bluez/{hci0,hci1,...}/dev_XX_XX_XX_XX_XX_XX`.

    """
    if not validate_mac_address(address):
        raise BleakError("{0} is not a valid MAC adrdess.".format(address))

    if not validate_hci_device(hci_device):
        raise BleakError("{0} is not a valid HCI device.".format(hci_device))

    # TODO: Join using urljoin? Or pathlib?
    return "/org/bluez/{0}/dev_{1}".format(
        hci_device, "_".join(address.split(":")).upper()
    )


def get_gatt_service_path(hci_device, address, service_id):
    """Get object path for a GATT Service for a Bluetooth device.

        Service         org.bluez
        Service         org.bluez
        Interface       org.bluez.GattService1
        Object path     [variable prefix]/{hci0,hci1,...}/dev_XX_XX_XX_XX_XX_XX/serviceXX

        Args:
            hci_device (str): Which bluetooth adapter to connect with.
            address (str): The MAC adress of the bluetooth device.
            service_id (int):

        Returns:
            String representation of GATT service object path on format
            `/org/bluez/{hci0,hci1,...}/dev_XX_XX_XX_XX_XX_XX/serviceXX`.

        """
    base = get_device_object_path(hci_device, address)
    return base + "{0}/service{1:02d}".format(base, service_id)


async def get_managed_objects(bus, loop, object_path_filter=None):
    objects = await bus.callRemote(
        "/",
        "GetManagedObjects",
        interface="org.freedesktop.DBus.ObjectManager",
        destination="org.bluez",
    ).asFuture(loop)
    if object_path_filter:
        return dict(
            filter(lambda i: i[0].startswith(object_path_filter), objects.items())
        )

    else:
        return objects


def format_GATT_object(object_path, interfaces):
    if defs.GATT_SERVICE_INTERFACE in interfaces:
        props = interfaces.get(defs.GATT_SERVICE_INTERFACE)
        _type = "{0} Service".format("Primary" if props.get("Primary") else "Secondary")
    elif defs.GATT_CHARACTERISTIC_INTERFACE in interfaces:
        props = interfaces.get(defs.GATT_CHARACTERISTIC_INTERFACE)
        _type = "Characteristic"
    elif defs.GATT_DESCRIPTOR_INTERFACE in interfaces:
        props = interfaces.get(defs.GATT_DESCRIPTOR_INTERFACE)
        _type = "Descriptor"
    else:
        return None

    _uuid = props.get("UUID")
    return "\n{0}\n\t{1}\n\t{2}\n\t{3}".format(
        _type, object_path, _uuid, uuidstr_to_str(_uuid)
    )
