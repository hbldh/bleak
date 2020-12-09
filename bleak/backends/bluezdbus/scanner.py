import logging
import asyncio
from typing import Any, Dict, List, Optional

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType, MessageType
from dbus_next.message import Message
from dbus_next.signature import Variant

from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.signals import MatchRules, add_match, remove_match
from bleak.backends.bluezdbus.utils import unpack_variants, validate_mac_address
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import BaseBleakScanner, AdvertisementData

logger = logging.getLogger(__name__)


def _device_info(path, props):
    try:
        name = props.get("Alias", "Unknown")
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
    except Exception:
        return None, None, None, None


class BleakScannerBlueZDBus(BaseBleakScanner):
    """The native Linux Bleak BLE Scanner.

    For possible values for `filters`, see the parameters to the
    ``SetDiscoveryFilter`` method in the `BlueZ docs
    <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/adapter-api.txt?h=5.48&id=0d1e3b9c5754022c779da129025d493a198d49cf>`_

    Keyword Args:
        adapter (str): Bluetooth adapter to use for discovery.
        filters (dict): A dict of filters to be applied on discovery.

    """

    def __init__(self, **kwargs):
        super(BleakScannerBlueZDBus, self).__init__(**kwargs)
        # kwarg "device" is for backwards compatibility
        self._adapter = kwargs.get("adapter", kwargs.get("device", "hci0"))

        self._bus: Optional[MessageBus] = None
        self._cached_devices: Dict[str, Variant] = {}
        self._devices: Dict[str, Any] = {}
        self._rules: List[MatchRules] = []
        self._adapter_path: str = f"/org/bluez/{self._adapter}"

        # Discovery filters
        self._filters: Dict[str, Variant] = {}
        self.set_scanning_filter(**kwargs)

    async def start(self):
        self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        # Add signal listeners

        self._bus.add_message_handler(self._parse_msg)

        rules = MatchRules(
            interface=defs.OBJECT_MANAGER_INTERFACE,
            member="InterfacesAdded",
            arg0path=f"{self._adapter_path}/",
        )
        reply = await add_match(self._bus, rules)
        assert reply.message_type == MessageType.METHOD_RETURN
        self._rules.append(rules)

        rules = MatchRules(
            interface=defs.OBJECT_MANAGER_INTERFACE,
            member="InterfacesRemoved",
            arg0path=f"{self._adapter_path}/",
        )
        reply = await add_match(self._bus, rules)
        assert reply.message_type == MessageType.METHOD_RETURN
        self._rules.append(rules)

        rules = MatchRules(
            interface=defs.PROPERTIES_INTERFACE,
            member="PropertiesChanged",
            path_namespace=self._adapter_path,
        )
        reply = await add_match(self._bus, rules)
        assert reply.message_type == MessageType.METHOD_RETURN
        self._rules.append(rules)

        # Find the HCI device to use for scanning and get cached device properties
        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path="/",
                member="GetManagedObjects",
                interface=defs.OBJECT_MANAGER_INTERFACE,
            )
        )
        assert reply.message_type == MessageType.METHOD_RETURN

        # get only the device interface
        self._cached_devices = {
            path: unpack_variants(interfaces[defs.DEVICE_INTERFACE])
            for path, interfaces in reply.body[0].items()
            if defs.DEVICE_INTERFACE in interfaces
        }

        # Apply the filters
        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._adapter_path,
                interface=defs.ADAPTER_INTERFACE,
                member="SetDiscoveryFilter",
                signature="a{sv}",
                body=[self._filters],
            )
        )
        assert reply.message_type == MessageType.METHOD_RETURN

        # Start scanning
        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._adapter_path,
                interface=defs.ADAPTER_INTERFACE,
                member="StartDiscovery",
            )
        )
        assert reply.message_type == MessageType.METHOD_RETURN

    async def stop(self):
        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._adapter_path,
                interface=defs.ADAPTER_INTERFACE,
                member="StopDiscovery",
            )
        )
        assert reply.message_type == MessageType.METHOD_RETURN

        for rule in self._rules:
            await remove_match(self._bus, rule)
        self._rules.clear()
        self._bus.remove_message_handler(self._parse_msg)

        # Try to disconnect the System Bus.
        try:
            self._bus.disconnect()
        except Exception as e:
            logger.error("Attempt to disconnect system bus failed: {0}".format(e))

        self._bus = None
        self._reactor = None

    def set_scanning_filter(self, **kwargs):
        """Sets OS level scanning filters for the BleakScanner.

        For possible values for `filters`, see the parameters to the
        ``SetDiscoveryFilter`` method in the `BlueZ docs
        <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/adapter-api.txt?h=5.48&id=0d1e3b9c5754022c779da129025d493a198d49cf>`_

        Keyword Args:
            filters (dict): A dict of filters to be applied on discovery.

        """
        self._filters = {k: Variant(v) for k, v in kwargs.get("filters", {}).items()}
        if "Transport" not in self._filters:
            self._filters["Transport"] = Variant("s", "le")

    async def get_discovered_devices(self) -> List[BLEDevice]:
        # Reduce output.
        discovered_devices = []
        for path, props in self._devices.items():
            if not props:
                logger.debug(
                    "Disregarding %s since no properties could be obtained." % path
                )
                continue
            name, address, _, path = _device_info(path, props)
            if address is None:
                continue
            uuids = props.get("UUIDs", [])
            manufacturer_data = props.get("ManufacturerData", {})
            discovered_devices.append(
                BLEDevice(
                    address,
                    name,
                    {"path": path, "props": props},
                    props.get("RSSI", 0),
                    uuids=uuids,
                    manufacturer_data=manufacturer_data,
                )
            )
        return discovered_devices

    # Helper methods

    def _update_devices(self, path: str, properties: Dict[str, Variant]):
        """Update the active devices based on the new properties.

        Args:
            path: The D-Bus path of the device.
            properties: New properties for this device.
        """
        # if this is the first time we have seen this device, use the cached
        # properties from ObjectManager.GetManagedObjects as a starting point
        # if they exist
        if path not in self._devices:
            self._devices[path] = {}
            self._update_devices(path, self._cached_devices.get(path, {}))

        # then update the existing properties with the new ones
        self._devices[path].update(properties)

    def _parse_msg(self, message: Message):
        if message.member == "InterfacesAdded":
            # if a new device is discovered while we are scanning, add it to
            # the discovered devices list

            msg_path = message.body[0]
            device_interface = unpack_variants(
                message.body[1].get(defs.DEVICE_INTERFACE, {})
            )
            self._update_devices(msg_path, device_interface)
            logger.debug(
                "{0}, {1} ({2}): {3}".format(
                    message.member, message.interface, message.path, message.body
                )
            )
        elif message.member == "InterfacesRemoved":
            # if a device disappears while we are scanning, remove it from the
            # discovered devices list

            msg_path = message.body[0]
            del self._devices[msg_path]
            logger.debug(
                "{0}, {1} ({2}): {3}".format(
                    message.member, message.interface, message.path, message.body
                )
            )
        elif message.member == "PropertiesChanged":
            # Property change events basically mean that new advertising data
            # was received or the RSSI changed. Either way, it lets us know
            # that the device is active and we can add it to the discovered
            # devices list.

            if message.body[0] != defs.DEVICE_INTERFACE:
                return

            changed = unpack_variants(message.body[1])
            self._update_devices(message.path, changed)

            logger.debug(
                "{0}, {1} ({2} dBm), Object Path: {3}".format(
                    *_device_info(message.path, self._devices.get(message.path))
                )
            )

            if self._callback is None:
                return

            props = self._devices[message.path]

            # Get all the information wanted to pack in the advertisement data
            _local_name = props.get("Name")
            _manufacturer_data = {
                k: bytes(v) for k, v in props.get("ManufacturerData", {}).items()
            }
            _service_data = {
                k: bytes(v) for k, v in props.get("ServiceData", {}).items()
            }
            _service_uuids = props.get("UUIDs", [])

            # Pack the advertisement data
            advertisement_data = AdvertisementData(
                local_name=_local_name,
                manufacturer_data=_manufacturer_data,
                service_data=_service_data,
                service_uuids=_service_uuids,
                platform_data=(props, message),
            )

            device = BLEDevice(
                props["Address"], props["Alias"], props, props.get("RSSI", 0)
            )

            self._callback(device, advertisement_data)
