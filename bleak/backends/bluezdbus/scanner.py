import logging
import asyncio
import pathlib
from typing import List

from bleak.backends.scanner import BaseBleakScanner, AdvertisementData
from bleak.backends.device import BLEDevice
from bleak.backends.bluezdbus import defs, get_reactor
from bleak.backends.bluezdbus.utils import validate_mac_address
from txdbus import client

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


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
        self._reactor = None
        self._bus = None

        self._cached_devices = {}
        self._devices = {}
        self._rules = list()

        # Discovery filters
        self._filters = kwargs.get("filters", {})
        if "Transport" not in self._filters:
            self._filters["Transport"] = "le"

        self._adapter_path = None
        self._interface = None

    async def start(self):
        loop = asyncio.get_event_loop()
        self._reactor = get_reactor(loop)
        self._bus = await client.connect(self._reactor, "system").asFuture(loop)

        # Add signal listeners
        self._rules.append(
            await self._bus.addMatch(
                self.parse_msg,
                interface="org.freedesktop.DBus.ObjectManager",
                member="InterfacesAdded",
            ).asFuture(loop)
        )

        self._rules.append(
            await self._bus.addMatch(
                self.parse_msg,
                interface="org.freedesktop.DBus.ObjectManager",
                member="InterfacesRemoved",
            ).asFuture(loop)
        )

        self._rules.append(
            await self._bus.addMatch(
                self.parse_msg,
                interface="org.freedesktop.DBus.Properties",
                member="PropertiesChanged",
            ).asFuture(loop)
        )

        # Find the HCI device to use for scanning and get cached device properties
        objects = await self._bus.callRemote(
            "/",
            "GetManagedObjects",
            interface=defs.OBJECT_MANAGER_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
        ).asFuture(loop)
        self._adapter_path, self._interface = _filter_on_adapter(objects, self._adapter)
        self._cached_devices = dict(_filter_on_device(objects))

        # Apply the filters
        await self._bus.callRemote(
            self._adapter_path,
            "SetDiscoveryFilter",
            interface="org.bluez.Adapter1",
            destination="org.bluez",
            signature="a{sv}",
            body=[self._filters],
        ).asFuture(loop)

        # Start scanning
        await self._bus.callRemote(
            self._adapter_path,
            "StartDiscovery",
            interface="org.bluez.Adapter1",
            destination="org.bluez",
        ).asFuture(loop)

    async def stop(self):
        loop = asyncio.get_event_loop()
        await self._bus.callRemote(
            self._adapter_path,
            "StopDiscovery",
            interface="org.bluez.Adapter1",
            destination="org.bluez",
        ).asFuture(loop)

        for rule in self._rules:
            await self._bus.delMatch(rule).asFuture(loop)
        self._rules.clear()

        # Try to disconnect the System Bus.
        try:
            self._bus.disconnect()
        except Exception as e:
            logger.error("Attempt to disconnect system bus failed: {0}".format(e))

        self._bus = None
        self._reactor = None

    async def set_scanning_filter(self, **kwargs):
        """Sets OS level scanning filters for the BleakScanner.

        For possible values for `filters`, see the parameters to the
        ``SetDiscoveryFilter`` method in the `BlueZ docs
        <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/adapter-api.txt?h=5.48&id=0d1e3b9c5754022c779da129025d493a198d49cf>`_

        Keyword Args:
            filters (dict): A dict of filters to be applied on discovery.

        """
        self._filters = kwargs.get("filters", {})
        if "Transport" not in self._filters:
            self._filters["Transport"] = "le"

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

    def parse_msg(self, message):
        if message.member == "InterfacesAdded":
            msg_path = message.body[0]
            try:
                device_interface = message.body[1].get(defs.DEVICE_INTERFACE, {})
            except Exception as e:
                raise e
            self._devices[msg_path] = (
                {**self._devices[msg_path], **device_interface}
                if msg_path in self._devices
                else device_interface
            )
        elif message.member == "PropertiesChanged":
            iface, changed, invalidated = message.body
            if iface != defs.DEVICE_INTERFACE:
                return

            msg_path = message.path
            # the PropertiesChanged signal only sends changed properties, so we
            # need to get remaining properties from cached_devices. However, we
            # don't want to add all cached_devices to the devices dict since
            # they may not actually be nearby or powered on.
            if msg_path not in self._devices and msg_path in self._cached_devices:
                self._devices[msg_path] = self._cached_devices[msg_path]
            self._devices[msg_path] = (
                {**self._devices[msg_path], **changed}
                if msg_path in self._devices
                else changed
            )

            if self._callback is None:
                return

            props = self._devices[msg_path]

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

        elif (
            message.member == "InterfacesRemoved"
            and message.body[1][0] == defs.BATTERY_INTERFACE
        ):
            logger.debug(
                "{0}, {1} ({2}): {3}".format(
                    message.member, message.interface, message.path, message.body
                )
            )
            return
        else:
            msg_path = message.path
            logger.debug(
                "{0}, {1} ({2}): {3}".format(
                    message.member, message.interface, message.path, message.body
                )
            )

        logger.debug(
            "{0}, {1} ({2} dBm), Object Path: {3}".format(
                *_device_info(msg_path, self._devices.get(msg_path))
            )
        )
