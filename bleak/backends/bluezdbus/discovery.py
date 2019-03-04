# -*- coding: utf-8 -*-

import asyncio
import logging

from bleak.backends.device import BLEDevice
from bleak.backends.bluezdbus import reactor, defs
from bleak.backends.bluezdbus.utils import validate_mac_address

# txdbus.client MUST be imported AFTER bleak.backends.bluezdbus.reactor!
from txdbus import client


logger = logging.getLogger(__name__)


def _filter_on_adapter(objs, pattern="hci0"):
    for path, interfaces in objs.items():
        adapter = interfaces.get("org.bluez.Adapter1")
        if adapter is None:
            continue

        if not pattern or pattern == adapter["Address"] or path.endswith(pattern):
            return path, interfaces

    raise Exception("Bluetooth adapter not found")


def _device_info(path, props):
    name = props.get("Name", props.get("Alias", path.split("/")[-1]))
    address = props.get("Address", None)
    if address is None:
        try:
            address = path[-17:].replace("_", ":")
            if not validate_mac_address(address):
                address = None
        except Exception:
            address = None
    rssi = props.get("RSSI", "?")
    return name, address, rssi, path


async def discover(timeout=5.0, loop=None, **kwargs):
    """Discover nearby Bluetooth Low Energy devices.

    Args:
        timeout (float): Duration to scan for.
        loop (asyncio.AbstractEventLoop): Optional event loop to use.

    Keyword Args:
        device (str): Bluetooth device to use for discovery.

    Returns:
        List of tuples containing name, address and signal strength
        of nearby devices.

    """
    device = kwargs.get("device", "hci0")
    loop = loop if loop else asyncio.get_event_loop()
    devices = {}

    def parse_msg(message):
        if message.member in ("InterfacesAdded", "InterfacesRemoved"):
            msg_path = message.body[0]
            device_interface = message.body[1].get("org.bluez.Device1", {})
            devices[msg_path] = (
                {**devices[msg_path], **device_interface}
                if msg_path in devices
                else device_interface
            )
        elif message.member == "PropertiesChanged":
            iface, changed, invalidated = message.body
            if iface != defs.DEVICE_INTERFACE:
                return

            msg_path = message.path
            devices[msg_path] = (
                {**devices[msg_path], **changed} if msg_path in devices else changed
            )
        else:
            msg_path = message.path
            logger.info(
                "{0}, {1} ({2}): {3}".format(
                    message.member, message.interface, message.path, message.body
                )
            )

        logger.info(
            "{0}, {1} ({2} dBm), Object Path: {3}".format(
                *_device_info(msg_path, devices.get(msg_path))
            )
        )

    # Find the HCI device to use for scanning.
    bus = await client.connect(reactor, "system").asFuture(loop)
    objects = await bus.callRemote(
        "/",
        "GetManagedObjects",
        interface=defs.OBJECT_MANAGER_INTERFACE,
        destination=defs.BLUEZ_SERVICE,
    ).asFuture(loop)
    adapter_path, interface = _filter_on_adapter(objects, device)

    # Add signal listeners
    await bus.addMatch(
        parse_msg,
        interface="org.freedesktop.DBus.ObjectManager",
        member="InterfacesAdded",
    ).asFuture(loop)
    await bus.addMatch(
        parse_msg,
        interface="org.freedesktop.DBus.ObjectManager",
        member="InterfacesRemoved",
    ).asFuture(loop)
    await bus.addMatch(
        parse_msg,
        interface="org.freedesktop.DBus.Properties",
        member="PropertiesChanged",
    ).asFuture(loop)
    await bus.addMatch(
        parse_msg, interface="org.bluez.Adapter1", member="PropertyChanged"
    ).asFuture(loop)

    # dd = {'objectPath': '/org/bluez/hci0', 'methodName': 'StartDiscovery',
    # 'interface': 'org.bluez.Adapter1', 'destination': 'org.bluez',
    # 'signature': '', 'body': (), 'expectReply': True, 'autoStart': True,
    # 'timeout': None, 'returnSignature': ''}
    # Running Discovery loop.
    await bus.callRemote(
        adapter_path,
        "StartDiscovery",
        interface="org.bluez.Adapter1",
        destination="org.bluez",
    ).asFuture(loop)
    await asyncio.sleep(timeout)
    await bus.callRemote(
        adapter_path,
        "StopDiscovery",
        interface="org.bluez.Adapter1",
        destination="org.bluez",
    ).asFuture(loop)

    # Reduce output.
    # out = []
    # for path, props in devices.items():
    #    properties = await cli.callRemote(
    #        path, 'GetAll',
    #        interface=defs.PROPERTIES_INTERFACE,
    #        destination=defs.BLUEZ_SERVICE,
    #        signature='s',
    #        body=[defs.DEVICE_INTERFACE, ],
    #        returnSignature='a{sv}').asFuture(loop)
    #    print(properties)
    #
    discovered_devices = []
    for path, props in devices.items():
        name, address, _, path = _device_info(path, props)
        discovered_devices.append(BLEDevice(address, name, path))
    return discovered_devices
