# -*- coding: utf-8 -*-
import logging
import asyncio
from functools import wraps
from typing import Callable, Any

from bleak.exc import BleakError
from bleak.backends.client import BaseBleakClient
from bleak.backends.bluezdbus import reactor, defs, signals, utils
from bleak.backends.bluezdbus.utils import get_device_object_path, get_managed_objects

# txdbus MUST be imported AFTER bleak.backends.bluezdbus.reactor!
from txdbus.client import connect as txdbus_connect
from txdbus.error import RemoteError

logger = logging.getLogger(__name__)


class BleakClientBlueZDBus(BaseBleakClient):
    """BlueZ DBUS BLE client."""

    def __init__(self, address, loop=None, **kwargs):
        super(BleakClientBlueZDBus, self).__init__(address, loop, **kwargs)
        self.device = kwargs.get("device") if kwargs.get("device") else "hci0"
        self.address = address

        # Backend specific, TXDBus objects and data
        self._device_path = None
        self._bus = None
        self._descriptors = {}
        self._rules = {}

        self._char_path_to_uuid = {}

    # Connectivity methods

    async def connect(self) -> bool:
        """Connect to the specified GATT server.

        Returns:
            Boolean representing connection status.

        """

        # Create system bus
        self._bus = await txdbus_connect(reactor, busAddress="system").asFuture(
            self.loop
        )
        # TODO: Handle path errors from txdbus/dbus
        self._device_path = get_device_object_path(self.device, self.address)

        def _services_resolved_callback(message):
            iface, changed, invalidated = message.body
            is_resolved = defs.DEVICE_INTERFACE and changed.get(
                "ServicesResolved", False
            )
            if iface == is_resolved:
                logger.info("Services resolved.")
                self.services_resolved = True

        rule_id = await signals.listen_properties_changed(
            self._bus, self.loop, _services_resolved_callback
        )

        logger.debug(
            "Connecting to BLE device @ {0} with {1}".format(self.address, self.device)
        )
        try:
            await self._bus.callRemote(
                self._device_path,
                "Connect",
                interface="org.bluez.Device1",
                destination="org.bluez",
            ).asFuture(self.loop)
        except RemoteError as e:
            raise BleakError(str(e))

        if await self.is_connected():
            logger.debug("Connection successful.")
        else:
            raise BleakError(
                "Connection to {0} was not successful!".format(self.address)
            )

        # Get all services. This means making the actual connection.
        await self.get_services()
        properties = await self._get_device_properties()
        if not properties.get("Connected"):
            raise BleakError("Connection failed!")

        await self._bus.delMatch(rule_id).asFuture(self.loop)
        self._rules["PropChanged"] = await signals.listen_properties_changed(
            self._bus, self.loop, self._properties_changed_callback
        )
        return True

    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        Returns:
            Boolean representing connection status.

        """
        logger.debug("Disconnecting from BLE device...")
        for rule_name, rule_id in self._rules.items():
            logger.debug("Removing rule {0}, ID: {1}".format(rule_name, rule_id))
            await self._bus.delMatch(rule_id).asFuture(self.loop)
        await self._bus.callRemote(
            self._device_path,
            "Disconnect",
            interface=defs.DEVICE_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
        ).asFuture(self.loop)
        return not await self.is_connected()

    async def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        # TODO: Listen to connected property changes.
        return await self._bus.callRemote(
            self._device_path,
            "Get",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="ss",
            body=[defs.DEVICE_INTERFACE, "Connected"],
            returnSignature="v",
        ).asFuture(self.loop)

    # GATT services methods

    async def get_services(self) -> dict:
        """Get all services registered for this GATT server.

        Returns:
            Dictionary of all service UUIDs as keys and
            service object's properties as values.

        """
        if self.services:
            return self.services

        while True:
            properties = await self._get_device_properties()
            services_resolved = properties.get("ServicesResolved", False)
            if services_resolved:
                break
            await asyncio.sleep(0.02, loop=self.loop)

        logger.debug("Get Services...")
        objs = await get_managed_objects(
            self._bus, self.loop, self._device_path + "/service"
        )
        self.services = {}
        self.characteristics = {}
        self._descriptors = {}
        for object_path, interfaces in objs.items():
            logger.debug(utils.format_GATT_object(object_path, interfaces))
            if defs.GATT_SERVICE_INTERFACE in interfaces:
                service = interfaces.get(defs.GATT_SERVICE_INTERFACE)
                self.services[service.get("UUID")] = service
                self.services[service.get("UUID")]["Path"] = object_path
            elif defs.GATT_CHARACTERISTIC_INTERFACE in interfaces:
                char = interfaces.get(defs.GATT_CHARACTERISTIC_INTERFACE)
                self.characteristics[char.get("UUID")] = char
                self.characteristics[char.get("UUID")]["Path"] = object_path
                self._char_path_to_uuid[object_path] = char.get("UUID")
            elif defs.GATT_DESCRIPTOR_INTERFACE in interfaces:
                desc = interfaces.get(defs.GATT_DESCRIPTOR_INTERFACE)
                self._descriptors[desc.get("UUID")] = desc
                self._descriptors[desc.get("UUID")]["Path"] = object_path

        self._services_resolved = True
        return self.services

    # IO methods

    async def read_gatt_char(self, _uuid: str) -> bytearray:
        """Read the data on a GATT characteristic.

        Args:
            _uuid (str or uuid.UUID): UUID for the characteristic to read from.

        Returns:
            Byte array of data.

        """
        char_props = self.characteristics.get(str(_uuid))
        if not char_props:
            # TODO: Raise error instead?
            return None

        value = bytearray(
            await self._bus.callRemote(
                char_props.get("Path"),
                "ReadValue",
                interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
                signature="a{sv}",
                body=[{}],
                returnSignature="ay",
            ).asFuture(self.loop)
        )

        logger.debug(
            "Read Characteristic {0} | {1}: {2}".format(
                _uuid, char_props.get("Path"), value
            )
        )
        return value

    async def write_gatt_char(
        self, _uuid: str, data: bytearray, response: bool = False
    ) -> Any:
        """Write data to a GATT characteristic.

        Args:
            _uuid (str or uuid.UUID): The UUID of the GATT
            characteristic to write to.
            data (bytearray):
            response (bool): Write with response.

        Returns:
            None if not `response=True`, in which case a bytearray is returned.

        """
        char_props = self.characteristics.get(str(_uuid))
        await self._bus.callRemote(
            char_props.get("Path"),
            "WriteValue",
            interface=defs.GATT_CHARACTERISTIC_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="aya{sv}",
            body=[data, {}],
            returnSignature="",
        ).asFuture(self.loop)
        logger.debug(
            "Write Characteristic {0} | {1}: {2}".format(
                _uuid, char_props.get("Path"), data
            )
        )
        if response:
            return await self.read_gatt_char(_uuid)

    async def start_notify(
        self, _uuid: str, callback: Callable[[str, Any], Any], **kwargs
    ) -> None:
        """Starts a notification session from a characteristic.

        Args:
            _uuid (str or uuid.UUID): The UUID of the GATT
            characteristic to start subscribing to notifications from.
            callback (Callable): A function that will be called on notification.

        Keyword Args:
            notification_wrapper (bool): Set to `False` to avoid parsing of
            notification to bytearray.

        """
        _wrap = kwargs.get("notification_wrapper", True)
        char_props = self.characteristics.get(_uuid)
        await self._bus.callRemote(
            char_props.get("Path"),
            "StartNotify",
            interface=defs.GATT_CHARACTERISTIC_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="",
            body=[],
            returnSignature="",
        ).asFuture(self.loop)

        if _wrap:
            self._notification_callbacks[
                char_props.get("Path")
            ] = _data_notification_wrapper(
                callback, self._char_path_to_uuid
            )  # noqa | E123 error in flake8...
        else:
            self._notification_callbacks[
                char_props.get("Path")
            ] = _regular_notification_wrapper(
                callback, self._char_path_to_uuid
            )  # noqa | E123 error in flake8...

    async def stop_notify(self, _uuid: str) -> None:
        """Stops a notification session from a characteristic.

        Args:
            _uuid (str or uuid.UUID): The UUID of the characteristic to stop
            subscribing to notifications from.

        """
        char_props = self.characteristics.get(_uuid)
        await self._bus.callRemote(
            char_props.get("Path"),
            "StopNotify",
            interface=defs.GATT_CHARACTERISTIC_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="",
            body=[],
            returnSignature="",
        ).asFuture(self.loop)
        self._notification_callbacks.pop(char_props.get("Path"), None)

    # DBUS introspection method for characteristics.

    async def get_all_for_characteristic(self, _uuid):
        char_props = self.characteristics.get(str(_uuid))
        out = await self._bus.callRemote(
            char_props.get("Path"),
            "GetAll",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="s",
            body=[defs.GATT_CHARACTERISTIC_INTERFACE],
            returnSignature="a{sv}",
        ).asFuture(self.loop)
        return out

    async def _get_device_properties(self):
        return await self._bus.callRemote(
            self._device_path,
            "GetAll",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="s",
            body=[defs.DEVICE_INTERFACE],
            returnSignature="a{sv}",
        ).asFuture(self.loop)

    # Internal Callbacks

    def _interface_added_callback(self, message):
        object_path = message.body[0]
        if not object_path.startswith(self._device_path):
            return

        interfaces = message.body[1]

        logger.debug("[NEW] " + utils.format_GATT_object(object_path, interfaces))
        if defs.GATT_SERVICE_INTERFACE in interfaces:
            service = interfaces.get(defs.GATT_SERVICE_INTERFACE)
            self.services[service.get("UUID")] = service
            self.services[service.get("UUID")]["Path"] = object_path
        elif defs.GATT_CHARACTERISTIC_INTERFACE in interfaces:
            char = interfaces.get(defs.GATT_CHARACTERISTIC_INTERFACE)
            self.characteristics[char.get("UUID")] = char
            self.characteristics[char.get("UUID")]["Path"] = object_path
        elif defs.GATT_DESCRIPTOR_INTERFACE in interfaces:
            desc = interfaces.get(defs.GATT_DESCRIPTOR_INTERFACE)
            self._descriptors[desc.get("UUID")] = desc
            self._descriptors[desc.get("UUID")]["Path"] = object_path

    def _interface_removed_callback(self, message):
        logger.debug("Interface Removed: {0}".format(message.body))

    def _properties_changed_callback(self, message):
        """Notification handler.

        If the BlueZ DBus API, notifications come as
        PropertiesChanged callbacks on the GATT Characteristic interface
        that StartNotify has been called on.

        Args:
            message (): The PropertiesChanged DBus signal message relaying
                the new data on the GATT Characteristic.

        """
        if message.body[0] == defs.GATT_CHARACTERISTIC_INTERFACE:
            if message.path in self._notification_callbacks:
                logger.info(
                    "GATT Char Properties Changed: {0} | {1}".format(
                        message.path, message.body[1:]
                    )
                )
                self._notification_callbacks[message.path](
                    message.path, message.body[1]
                )


def _data_notification_wrapper(func, char_map):
    @wraps(func)
    def args_parser(sender, data):
        if "Value" in data:
            # Do a conversion from {'Value': [...]} to bytearray.
            return func(char_map.get(sender, sender), bytearray(data.get("Value")))

    return args_parser


def _regular_notification_wrapper(func, char_map):
    @wraps(func)
    def args_parser(sender, data):
        return func(char_map.get(sender, sender), data)

    return args_parser
