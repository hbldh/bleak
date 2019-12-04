# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import Callable

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


def _filter_on_device(objs):
    for path, interfaces in objs.items():
        device = interfaces.get("org.bluez.Device1")
        if device is None:
            continue

        yield path, device


def _device_info(path, props):
    try:
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
    except Exception as e:
        # logger.exception(e, exc_info=True)
        return None, None, None, None


def _parse_device(path, props):
    if not props:
        logger.debug(
            "Disregarding %s since no properties could be obtained." % path
        )
        return None

    name, address, _, path = _device_info(path, props)
    if address is None:
        return None

    uuids = props.get("UUIDs", [])
    manufacturer_data = props.get("ManufacturerData", {})
    return BLEDevice(
            address,
            name,
            {"path": path, "props": props},
            uuids=uuids,
            manufacturer_data=manufacturer_data,
        )


class AsyncDiscovery():

    def __init__(self, callback: Callable[[BLEDevice], None]=None,
                 loop=None, device="hci0"):
        """State keeper to discover nearby Bluetooth Low Energy devices and get
        a call for each discovered device in an asynchronous way.

        Args:
            callback (Callable[[bleak.BLEDevice], None]): called for each discovered device.
            loop (asyncio.AbstractEventLoop): Optional event loop to use.
            device (str): Bluetooth device to use for discovery.

        """
        self.callback = callback
        self.device = device
        self.loop = loop if loop else asyncio.get_event_loop()
        self.rules = list()
        self.cached_devices = {}
        self.bus = None
        self.devices = {}
        self.adapter_path = ""

    async def _start_discovery(self, filters=None):
        """Start discovering of nearby BLE devices.

        For possible values for `filters`, see the parameters to the
        ``SetDiscoveryFilter`` method in the `BlueZ docs
        <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/adapter-api.txt?h=5.48&id=0d1e3b9c5754022c779da129025d493a198d49cf>`_

        The ``Transport`` parameter is always set to ``le`` by default in Bleak.

        The filters are applied and the callback registered with the object is
        called every time a new device appears or the properties of an already
        discovered device changes. This might happen frequently, since a change
        in the RSSI value is considered a property change.

        Args:
            filters (dict): A dict of filters to be applied on discovery.

        """
        if self.rules:
            # List is not empty, scanning is already in progress.
            return

        if not filters:
            filters = dict()

        filters["Transport"] = "le"

        self.bus = await client.connect(reactor, "system").asFuture(self.loop)

        # Add signal listeners
        self.rules.append(
            await self.bus.addMatch(
                self._parse_msg,
                interface="org.freedesktop.DBus.ObjectManager",
                member="InterfacesAdded",
            ).asFuture(self.loop)
        )
        self.rules.append(
            await self.bus.addMatch(
                self._parse_msg,
                interface="org.freedesktop.DBus.ObjectManager",
                member="InterfacesRemoved",
            ).asFuture(self.loop)
        )
        self.rules.append(
            await self.bus.addMatch(
                self._parse_msg,
                interface="org.freedesktop.DBus.Properties",
                member="PropertiesChanged",
            ).asFuture(self.loop)
        )

        # Find the HCI device to use for scanning and get cached device properties
        objects = await self.bus.callRemote(
            "/",
            "GetManagedObjects",
            interface=defs.OBJECT_MANAGER_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
        ).asFuture(self.loop)
        self.adapter_path, interface = _filter_on_adapter(objects, self.device)
        self.cached_devices = dict(_filter_on_device(objects))

        await self.bus.callRemote(
            self.adapter_path,
            "SetDiscoveryFilter",
            interface="org.bluez.Adapter1",
            destination="org.bluez",
            signature="a{sv}",
            body=[filters],
        ).asFuture(self.loop)
        await self.bus.callRemote(
            self.adapter_path,
            "StartDiscovery",
            interface="org.bluez.Adapter1",
            destination="org.bluez",
        ).asFuture(self.loop)

    async def stop_discovery(self):
        """
        Stop looking for nearby devices and provide a list of all devices
        discovered in the discovery session. If a device has been advertising
        but became unavailable before the discovery session ended, it will still
        show up in the returned list.

        Returns:
            List of BLEDevices that have been discovered.

        """
        if not self.rules:
            # Discovery is currently not active.
            return None

        await self.bus.callRemote(
            self.adapter_path,
            "StopDiscovery",
            interface="org.bluez.Adapter1",
            destination="org.bluez",
        ).asFuture(self.loop)

        for rule in self.rules:
            await self.bus.delMatch(rule).asFuture(self.loop)
            self.rules.remove(rule)

        self.bus.disconnect()
        discovered_devices = []

        for path, props in self.devices.items():
            discovered = _parse_device(path, props)
            if discovered:
                discovered_devices.append(discovered)

        return discovered_devices

    def _parse_msg(self, message):
        if message.member == "InterfacesAdded":
            msg_path = message.body[0]
            try:
                device_interface = message.body[1].get("org.bluez.Device1", {})
            except Exception as e:
                raise e
            self.devices[msg_path] = (
                {**self.devices[msg_path], **device_interface}
                if msg_path in self.devices
                else device_interface
            )

            dev = _parse_device(msg_path, self.devices[msg_path])
            if dev and self.callback:
                self.callback(dev)

        elif message.member == "PropertiesChanged":
            iface, changed, invalidated = message.body
            if iface != defs.DEVICE_INTERFACE:
                return

            msg_path = message.path
            # the PropertiesChanged signal only sends changed properties, so we
            # need to get remaining properties from cached_devices. However, we
            # don't want to add all cached_devices to the devices dict since
            # they may not actually be nearby or powered on.
            if msg_path not in self.devices and msg_path in self.cached_devices:
                self.devices[msg_path] = self.cached_devices[msg_path]
            self.devices[msg_path] = (
                {**self.devices[msg_path], **changed} if msg_path in self.devices else changed
            )

            dev = _parse_device(msg_path, self.devices[msg_path])
            if dev and self.callback:
                self.callback(dev)

        elif (
            message.member == "InterfacesRemoved"
            and message.body[1][0] == defs.BATTERY_INTERFACE
        ):
            logger.info(
                "{0}, {1} ({2}): {3}".format(
                    message.member, message.interface, message.path, message.body
                )
            )
            return
        else:
            msg_path = message.path
            logger.info(
                "{0}, {1} ({2}): {3}".format(
                    message.member, message.interface, message.path, message.body
                )
            )

        logger.info(
            "{0}, {1} ({2} dBm), Object Path: {3}".format(
                *_device_info(msg_path, self.devices.get(msg_path))
            )
        )

async def discover_async(callback: Callable[[BLEDevice], None]=None,
                         loop=None, **kwargs):
    """Start discovering asynchronously nearby Bluetooth Low Energy devices.
    The filters are applied and the callback registered with the object is
    called every time a new device appears or the properties of an already
    discovered device changes. This might happen frequently, since a change in
    the RSSI value is considered a property change.

    Args:
        callback (Callable[[bleak.BLEDevice], None]): called for each discovered device.
        loop (asyncio.AbstractEventLoop): Optional event loop to use.

    Keyword Args:
        device (str): Bluetooth device to use for discovery.
        filters (dict): A dict of filters to be applied on discovery.

    Returns:
        A discovery state object that can be used to stop the discovery again.

    """
    device = kwargs.get("device", "hci0")

    # Discovery filters
    filters = kwargs.get("filters", {})

    disco = AsyncDiscovery(callback, loop, device)
    await disco._start_discovery(filters)

    return disco


async def discover(timeout=5.0, loop=None, **kwargs):
    """Discover nearby Bluetooth Low Energy devices.

    For possible values for `filter`, see the parameters to the
    ``SetDiscoveryFilter`` method in the `BlueZ docs
    <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/adapter-api.txt?h=5.48&id=0d1e3b9c5754022c779da129025d493a198d49cf>`_

    The ``Transport`` parameter is always set to ``le`` by default in Bleak.

    Args:
        timeout (float): Duration to scan for.
        loop (asyncio.AbstractEventLoop): Optional event loop to use.

    Keyword Args:
        device (str): Bluetooth device to use for discovery.
        filters (dict): A dict of filters to be applied on discovery.

    Returns:
        List of tuples containing name, address and signal strength
        of nearby devices.

    """

    disco = await discover_async(None, loop, **kwargs)
    await asyncio.sleep(timeout)
    return await disco.stop_discovery()
