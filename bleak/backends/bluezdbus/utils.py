# -*- coding: utf-8 -*-
import re
from typing import Any, Dict, Union

from bleak.backends.bluezdbus import defs
from dbus_next.aio import MessageBus
from dbus_next.constants import MessageType, BusType
from dbus_next.message import Message
from dbus_next.signature import Variant

from bleak import BleakError
from bleak.exc import BleakDBusError

_mac_address_regex = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


def assert_reply(reply: Message):
    """Checks that a D-Bus message is a valid reply.

    Raises:
        BleakDBusError: if the message type is ``MessageType.ERROR``
        AssentationError: if the message type is not ``MessageType.METHOD_RETURN``
    """
    if reply.message_type == MessageType.ERROR:
        raise BleakDBusError(reply.error_name, reply.body)
    assert reply.message_type == MessageType.METHOD_RETURN


def validate_mac_address(address):
    return _mac_address_regex.match(address) is not None


def unpack_variants(dictionary: Dict[str, Variant]) -> Dict[str, Any]:
    """Recursively unpacks all ``Variant`` types in a dictionary to their
    corresponding Python types.

    ``dbus-next`` doesn't automatically do this, so this needs to be called on
    all dictionaries ("a{sv}") returned from D-Bus messages.
    """
    unpacked = {}
    for k, v in dictionary.items():
        v = v.value if isinstance(v, Variant) else v
        if isinstance(v, dict):
            v = unpack_variants(v)
        elif isinstance(v, list):
            v = [x.value if isinstance(x, Variant) else x for x in v]
        unpacked[k] = v
    return unpacked


def extract_service_handle_from_path(path):
    try:
        return int(path[-4:], 16)
    except Exception as e:
        raise BleakError(f"Could not parse service handle from path: {path}") from e


async def get_default_adapter(bus_or_reply: Union[Message, MessageBus] = None) -> str:
    """Get name of the first powered Bluetooth adapter

    Args:
        bus_or_reply (`Message` or `MessageBus`): Optional reply of already executed ``GetManagedObjects``
            D-Bus call to avoid executing this expensive operation again. Alternatively, if no such call
            was executed yet, active (connected) D-Bus connection can be provided if available to at least
            avoid creating new connection. Otherwise, new D-Bus connection will be created, used to call
            ``GetManagedObjects`` and closed afterwards.

    Returns:
        Name of the first found powered adapter on the system, available on D-Bus path "/org/bluez/<name>".

    Raises:
        OSError: if there are no Bluetooth adapters (D-Bus objects implementing org.bluez.Adapter1
            interface) on the system.
        OSError: if all found adapters are powered off - use `bluetoothctl power on` to power on the adapter.
    """
    if isinstance(bus_or_reply, Message):
        # No need to execute any D-Bus operation as its return message is already provided
        reply = bus_or_reply
    else:
        # Ensure that the message bus is valid and connected
        if isinstance(bus_or_reply, MessageBus) and bus_or_reply.connected:
            bus_created = False
        else:
            bus_or_reply = await MessageBus(bus_type=BusType.SYSTEM).connect()
            bus_created = True

        # Execute D-Bus operation
        reply = await bus_or_reply.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path="/",
                member="GetManagedObjects",
                interface=defs.OBJECT_MANAGER_INTERFACE,
            )
        )

        if bus_created:
            bus_or_reply.disconnect()

    # D-Bus reply shall be valid in all cases
    assert_reply(reply)

    all_adapters = []
    powered_adapters = []
    for path, interfaces in reply.body[0].items():
        for interface, properties in interfaces.items():
            if interface == defs.ADAPTER_INTERFACE:
                all_adapters.append(path)
                if properties["Powered"].value:
                    powered_adapters.append(path)

    if not all_adapters:
        raise OSError("No Bluetooth adapters found")
    if not powered_adapters:
        raise OSError(
            f"All available adapters ({', '.join(all_adapters)}) are powered off"
        )

    return powered_adapters[0].rsplit("/", 1)[-1]
