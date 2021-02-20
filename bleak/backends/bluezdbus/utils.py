# -*- coding: utf-8 -*-
import asyncio
import re

from bleak import BleakError
from bleak.uuids import uuidstr_to_str

from bleak.backends.bluezdbus import defs

_mac_address_regex = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
_service_handle_regex = re.compile('service([0-9A-Fa-f]*)')


def validate_mac_address(address):
    return _mac_address_regex.match(address) is not None


async def get_managed_objects(bus, object_path_filter=None):
    objects = await bus.callRemote(
        "/",
        "GetManagedObjects",
        interface="org.freedesktop.DBus.ObjectManager",
        destination="org.bluez",
    ).asFuture(asyncio.get_event_loop())
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


def extract_service_handle_from_path(path):
    try:
        return int(_service_handle_regex.search(path).groups()[-1], 16)
    except Exception as e:
        raise BleakError(f"Could not parse service handle from path: {path} ({e})")

