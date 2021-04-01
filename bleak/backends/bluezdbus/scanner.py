import logging
from typing import Any, Dict, List, Optional

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType, MessageType
from dbus_next.message import Message
from dbus_next.signature import Variant

from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.signals import MatchRules, add_match, remove_match
from bleak.backends.bluezdbus.utils import (
    assert_reply,
    unpack_variants,
    validate_mac_address,
)
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import BaseBleakScanner, AdvertisementData

logger = logging.getLogger(__name__)

# set of org.bluez.Device1 property names that come from advertising data
_ADVERTISING_DATA_PROPERTIES = {
    "AdvertisingData",
    "AdvertisingFlags",
    "ManufacturerData",
    "Name",
    "ServiceData",
    "UUIDs",
}


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
        self._devices: Dict[str, Dict[str, Any]] = {}
        self._rules: List[MatchRules] = []
        self._adapter_path: str = f"/org/bluez/{self._adapter}"

        # Discovery filters
        self._filters: Dict[str, Variant] = {}
        self.set_scanning_filter(**kwargs)

    async def start(self):
        self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        self._devices.clear()
        self._cached_devices.clear()

        # Add signal listeners

        self._bus.add_message_handler(self._parse_msg)

        rules = MatchRules(
            interface=defs.OBJECT_MANAGER_INTERFACE,
            member="InterfacesAdded",
            arg0path=f"{self._adapter_path}/",
        )
        reply = await add_match(self._bus, rules)
        assert_reply(reply)
        self._rules.append(rules)

        rules = MatchRules(
            interface=defs.OBJECT_MANAGER_INTERFACE,
            member="InterfacesRemoved",
            arg0path=f"{self._adapter_path}/",
        )
        reply = await add_match(self._bus, rules)
        assert_reply(reply)
        self._rules.append(rules)

        rules = MatchRules(
            interface=defs.PROPERTIES_INTERFACE,
            member="PropertiesChanged",
            path_namespace=self._adapter_path,
        )
        reply = await add_match(self._bus, rules)
        assert_reply(reply)
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
        assert_reply(reply)

        # get only the device interface
        self._cached_devices = {
            path: unpack_variants(interfaces[defs.DEVICE_INTERFACE])
            for path, interfaces in reply.body[0].items()
            if defs.DEVICE_INTERFACE in interfaces
        }

        logger.debug(f"cached devices: {self._cached_devices}")

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
        assert_reply(reply)

        # Start scanning
        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._adapter_path,
                interface=defs.ADAPTER_INTERFACE,
                member="StartDiscovery",
            )
        )
        assert_reply(reply)

    async def stop(self):
        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._adapter_path,
                interface=defs.ADAPTER_INTERFACE,
                member="StopDiscovery",
            )
        )
        assert_reply(reply)

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

    def set_scanning_filter(self, **kwargs):
        """Sets OS level scanning filters for the BleakScanner.

        For possible values for `filters`, see the parameters to the
        ``SetDiscoveryFilter`` method in the `BlueZ docs
        <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/adapter-api.txt?h=5.48&id=0d1e3b9c5754022c779da129025d493a198d49cf>`_

        See variant types here: <https://python-dbus-next.readthedocs.io/en/latest/type-system/>

        Keyword Args:
            filters (dict): A dict of filters to be applied on discovery.

        """
        for k, v in kwargs.get("filters", {}).items():
            if k == "UUIDs":
                self._filters[k] = Variant("as", v)
            elif k == "RSSI":
                self._filters[k] = Variant("n", v)
            elif k == "DuplicateData":
                self._filters[k] = Variant("b", v)
            elif k == "Pathloss":
                self._filters[k] = Variant("n", v)
            elif k == "Transport":
                self._filters[k] = Variant("s", v)
            else:
                logger.warning("Filter '%s' is not currently supported." % k)

        if "Transport" not in self._filters:
            self._filters["Transport"] = Variant("s", "le")

    @property
    def discovered_devices(self) -> List[BLEDevice]:
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

    def _invoke_callback(self, path: str, message: Message) -> None:
        """Invokes the advertising data callback.

        Args:
            message: The D-Bus message that triggered the callback.
        """
        if self._callback is None:
            return

        props = self._devices[path]

        # Get all the information wanted to pack in the advertisement data
        _local_name = props.get("Name")
        _manufacturer_data = {
            k: bytes(v) for k, v in props.get("ManufacturerData", {}).items()
        }
        _service_data = {k: bytes(v) for k, v in props.get("ServiceData", {}).items()}
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
            props["Address"],
            props["Alias"],
            {"path": path, "props": props},
            props.get("RSSI", 0),
        )

        self._callback(device, advertisement_data)

    def _parse_msg(self, message: Message):
        if message.message_type != MessageType.SIGNAL:
            return

        logger.debug(
            "received D-Bus signal: {0}.{1} ({2}): {3}".format(
                message.interface, message.member, message.path, message.body
            )
        )

        if message.member == "InterfacesAdded":
            # if a new device is discovered while we are scanning, add it to
            # the discovered devices list

            obj_path: str
            interfaces_and_props: Dict[str, Dict[str, Variant]]
            obj_path, interfaces_and_props = message.body
            device_props = unpack_variants(
                interfaces_and_props.get(defs.DEVICE_INTERFACE, {})
            )
            if device_props:
                self._devices[obj_path] = device_props
                self._invoke_callback(obj_path, message)
        elif message.member == "InterfacesRemoved":
            # if a device disappears while we are scanning, remove it from the
            # discovered devices list

            obj_path: str
            interfaces: List[str]
            obj_path, interfaces = message.body

            if defs.DEVICE_INTERFACE in interfaces:
                # Using pop to avoid KeyError if obj_path does not exist
                self._devices.pop(obj_path, None)
        elif message.member == "PropertiesChanged":
            # Property change events basically mean that new advertising data
            # was received or the RSSI changed. Either way, it lets us know
            # that the device is active and we can add it to the discovered
            # devices list.

            interface: str
            changed: Dict[str, Variant]
            invalidated: List[str]
            interface, changed, invalidated = message.body

            if interface != defs.DEVICE_INTERFACE:
                return

            first_time_seen = False

            if message.path not in self._devices:
                if message.path not in self._cached_devices:
                    # This can happen when we start scanning. The "PropertyChanged"
                    # handler is attached before "GetManagedObjects" is called
                    # and so self._cached_devices is not assigned yet.
                    # This is not a problem. We just discard the property value
                    # since "GetManagedObjects" will return a newer value.
                    return

                first_time_seen = True
                self._devices[message.path] = self._cached_devices[message.path]

            changed = unpack_variants(changed)
            self._devices[message.path].update(changed)

            # Only do advertising data callback if this is the first time the
            # device has been seen or if an advertising data property changed.
            # Otherwise we get a flood of callbacks from RSSI changing.
            if first_time_seen or not _ADVERTISING_DATA_PROPERTIES.isdisjoint(
                changed.keys()
            ):
                self._invoke_callback(message.path, message)
