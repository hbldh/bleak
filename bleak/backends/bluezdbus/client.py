# -*- coding: utf-8 -*-
import logging
import asyncio
import os
import re
import subprocess
from functools import wraps
from typing import Callable, Any

from bleak.backends.service import BleakGATTServiceCollection
from bleak.exc import BleakError
from bleak.backends.client import BaseBleakClient
from bleak.backends.bluezdbus import reactor, defs, signals, utils
from bleak.backends.bluezdbus.discovery import discover
from bleak.backends.bluezdbus.utils import get_device_object_path, get_managed_objects
from bleak.backends.bluezdbus.service import BleakGATTServiceBlueZDBus
from bleak.backends.bluezdbus.characteristic import BleakGATTCharacteristicBlueZDBus
from bleak.backends.bluezdbus.descriptor import BleakGATTDescriptorBlueZDBus

# txdbus MUST be imported AFTER bleak.backends.bluezdbus.reactor!
from txdbus.client import connect as txdbus_connect
from txdbus.error import RemoteError

logger = logging.getLogger(__name__)


class BleakClientBlueZDBus(BaseBleakClient):
    """A native Linux Bleak Client

    Implemented by using the `BlueZ DBUS API <https://docs.ubuntu.com/core/en/stacks/bluetooth/bluez/docs/reference/dbus-api>`_.
    """

    def __init__(self, address, loop=None, **kwargs):
        super(BleakClientBlueZDBus, self).__init__(address, loop, **kwargs)
        self.device = kwargs.get("device") if kwargs.get("device") else "hci0"
        self.address = address

        # Backend specific, TXDBus objects and data
        self._device_path = None
        self._bus = None
        self._rules = {}

        self._char_path_to_uuid = {}

        # We need to know BlueZ version since battery level characteristic
        # are stored in a separate DBus interface in the BlueZ >= 5.48.
        p = subprocess.Popen(["bluetoothctl", "--version"], stdout=subprocess.PIPE)
        out, _ = p.communicate()
        s = re.search(b"(\\d+).(\\d+)", out.strip(b"'"))
        self._bluez_version = tuple(map(int, s.groups()))

    # Connectivity methods

    async def connect(self) -> bool:
        """Connect to the specified GATT server.

        Returns:
            Boolean representing connection status.

        """

        # A Discover must have been run before connecting to any devices. Do a quick one here
        # to ensure that it has been done.
        await discover(timeout=0.1, loop=self.loop)

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

    async def get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self._services_resolved:
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

        for object_path, interfaces in objs.items():
            logger.debug(utils.format_GATT_object(object_path, interfaces))
            if defs.GATT_SERVICE_INTERFACE in interfaces:
                service = interfaces.get(defs.GATT_SERVICE_INTERFACE)
                self.services.add_service(
                    BleakGATTServiceBlueZDBus(service, object_path)
                )
            elif defs.GATT_CHARACTERISTIC_INTERFACE in interfaces:
                char = interfaces.get(defs.GATT_CHARACTERISTIC_INTERFACE)
                _service = list(
                    filter(lambda x: x.path == char["Service"], self.services)
                )
                self.services.add_characteristic(
                    BleakGATTCharacteristicBlueZDBus(
                        char, object_path, _service[0].uuid
                    )
                )
                self._char_path_to_uuid[object_path] = char.get("UUID")
            elif defs.GATT_DESCRIPTOR_INTERFACE in interfaces:
                desc = interfaces.get(defs.GATT_DESCRIPTOR_INTERFACE)
                _characteristic = list(
                    filter(
                        lambda x: x.path == desc["Characteristic"],
                        self.services.characteristics.values(),
                    )
                )
                self.services.add_descriptor(
                    BleakGATTDescriptorBlueZDBus(
                        desc, object_path, _characteristic[0].uuid
                    )
                )

        self._services_resolved = True
        return self.services

    # IO methods

    async def read_gatt_char(self, _uuid: str, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            _uuid (str or UUID): The uuid of the characteristics to read from.

        Returns:
            (bytearray) The read data.

        """
        characteristic = self.services.get_characteristic(str(_uuid))
        if not characteristic:
            # Special handling for BlueZ >= 5.48, where Battery Service (0000180f-0000-1000-8000-00805f9b34fb:)
            # has been moved to interface org.bluez.Battery1 instead of as a regular service.
            if _uuid == "00002a19-0000-1000-8000-00805f9b34fb" and (
                self._bluez_version[0] == 5 and self._bluez_version[1] >= 48
            ):
                props = await self._get_device_properties(
                    interface=defs.BATTERY_INTERFACE
                )
                # Simulate regular characteristics read to be consistent over all platforms.
                value = bytearray([props.get("Percentage", "")])
                logger.debug(
                    "Read Battery Level {0} | {1}: {2}".format(
                        _uuid, self._device_path, value
                    )
                )
                return value
            raise BleakError(
                "Characteristic with UUID {0} could not be found!".format(_uuid)
            )

        value = bytearray(
            await self._bus.callRemote(
                characteristic.path,
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
                _uuid, characteristic.path, value
            )
        )
        return value

    async def read_gatt_descriptor(self, handle: int, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.

        Returns:
            (bytearray) The read data.

        """
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            # TODO: Raise error instead?
            return None

        value = bytearray(
            await self._bus.callRemote(
                descriptor.path,
                "ReadValue",
                interface=defs.GATT_DESCRIPTOR_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
                signature="a{sv}",
                body=[{}],
                returnSignature="ay",
            ).asFuture(self.loop)
        )

        logger.debug(
            "Read Descriptor {0} | {1}: {2}".format(handle, descriptor.path, value)
        )
        return value

    async def write_gatt_char(
        self, _uuid: str, data: bytearray, response: bool = False
    ) -> None:
        """Perform a write operation on the specified GATT characteristic.

        Args:
            _uuid (str or UUID): The uuid of the characteristics to write to.
            data (bytes or bytearray): The data to send.
            response (bool): If write-with-response operation should be done. Defaults to `False`.

        """
        characteristic = self.services.get_characteristic(str(_uuid))
        if response or (self._bluez_version[0] == 5 and self._bluez_version[1] > 50):
            # TODO: Add OnValueUpdated handler for response=True?
            await self._bus.callRemote(
                characteristic.path,
                "WriteValue",
                interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
                signature="aya{sv}",
                body=[data, {"type": "request" if response else "command"}],
                returnSignature="",
            ).asFuture(self.loop)
        else:
            # Older versions of BlueZ don't have the "type" option, so we have
            # to write the hard way. This isn't the most efficient way of doing
            # things, but it works. Also, watch out for txdbus bug that causes
            # returned fd to be None. https://github.com/cocagne/txdbus/pull/81
            fd, _ = await self._bus.callRemote(
                characteristic.path,
                "AcquireWrite",
                interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
                signature="a{sv}",
                body=[{}],
                returnSignature="hq",
            ).asFuture(self.loop)
            os.write(fd, data)
            os.close(fd)

        logger.debug(
            "Write Characteristic {0} | {1}: {2}".format(
                _uuid, characteristic.path, data
            )
        )

    async def write_gatt_descriptor(self, handle: int, data: bytearray) -> None:

        """Perform a write operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            data (bytes or bytearray): The data to send.

        """
        return await super().write_gatt_descriptor(handle, data)

    async def start_notify(
        self, _uuid: str, callback: Callable[[str, Any], Any], **kwargs
    ) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept two inputs. The first will be a uuid string
        object and the second will be a bytearray.

        .. code-block:: python

            def callback(sender, data):
                print(f"{sender}: {data}")
            client.start_notify(char_uuid, callback)

        Args:
            _uuid (str or UUID): The uuid of the characteristics to start notification on.
            callback (function): The function to be called on notification.

        Keyword Args:
            notification_wrapper (bool): Set to `False` to avoid parsing of
                notification to bytearray.

        """
        _wrap = kwargs.get("notification_wrapper", True)
        characteristic = self.services.get_characteristic(str(_uuid))
        if not characteristic:
            # Special handling for BlueZ >= 5.48, where Battery Service (0000180f-0000-1000-8000-00805f9b34fb:)
            # has been moved to interface org.bluez.Battery1 instead of as a regular service.
            # The org.bluez.Battery1 on the other hand does not provide a notification method, so here we cannot
            # provide this functionality...
            # See https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/refs/tags/5.48/doc/battery-api.txt
            if _uuid == "00002a19-0000-1000-8000-00805f9b34fb" and (
                self._bluez_version[0] == 5 and self._bluez_version[1] >= 48
            ):
                raise BleakError(
                    "Notifications on Battery Level Char ({0}) is not "
                    "possible in BlueZ >= 5.48. Use regular read instead.".format(_uuid)
                )
            raise BleakError(
                "Characteristic with UUID {0} could not be found!".format(_uuid)
            )
        await self._bus.callRemote(
            characteristic.path,
            "StartNotify",
            interface=defs.GATT_CHARACTERISTIC_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="",
            body=[],
            returnSignature="",
        ).asFuture(self.loop)

        if _wrap:
            self._notification_callbacks[
                characteristic.path
            ] = _data_notification_wrapper(
                callback, self._char_path_to_uuid
            )  # noqa | E123 error in flake8...
        else:
            self._notification_callbacks[
                characteristic.path
            ] = _regular_notification_wrapper(
                callback, self._char_path_to_uuid
            )  # noqa | E123 error in flake8...

    async def stop_notify(self, _uuid: str) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            _uuid: The characteristic to stop notifying/indicating on.

        """
        characteristic = self.services.get_characteristic(str(_uuid))
        await self._bus.callRemote(
            characteristic.path,
            "StopNotify",
            interface=defs.GATT_CHARACTERISTIC_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="",
            body=[],
            returnSignature="",
        ).asFuture(self.loop)
        self._notification_callbacks.pop(characteristic.path, None)

    # DBUS introspection method for characteristics.

    async def get_all_for_characteristic(self, _uuid) -> dict:
        """Get all properties for a characteristic.

        This method should generally not be needed by end user, since it is a DBus specific method.

        Args:
            _uuid: The characteristic to get properties for.

        Returns:
            (dict) Properties dictionary

        """
        characteristic = self.services.get_characteristic(str(_uuid))
        out = await self._bus.callRemote(
            characteristic.path,
            "GetAll",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="s",
            body=[defs.GATT_CHARACTERISTIC_INTERFACE],
            returnSignature="a{sv}",
        ).asFuture(self.loop)
        return out

    async def _get_device_properties(self, interface=defs.DEVICE_INTERFACE) -> dict:
        """Get properties of the connected device.

        Args:
            interface: Which DBus interface to get properties on. Defaults to `org.bluez.Device1`.

        Returns:
            (dict) The properties.

        """
        return await self._bus.callRemote(
            self._device_path,
            "GetAll",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="s",
            body=[interface],
            returnSignature="a{sv}",
        ).asFuture(self.loop)

    # Internal Callbacks

    def _properties_changed_callback(self, message):
        """Notification handler.

        In the BlueZ DBus API, notifications come as
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
