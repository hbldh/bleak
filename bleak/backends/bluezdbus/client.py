# -*- coding: utf-8 -*-
"""
BLE Client for BlueZ on Linux
"""
import logging
import asyncio
import os
import re
import subprocess
import uuid
import warnings
from asyncio import Future
from functools import wraps, partial
from typing import Callable, Any, Union

from twisted.internet.error import ConnectionDone

from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakError
from bleak.backends.client import BaseBleakClient
from bleak.backends.bluezdbus import defs, signals, utils, get_reactor
from bleak.backends.bluezdbus.scanner import BleakScannerBlueZDBus
from bleak.backends.bluezdbus.utils import get_device_object_path, get_managed_objects
from bleak.backends.bluezdbus.service import BleakGATTServiceBlueZDBus
from bleak.backends.bluezdbus.characteristic import BleakGATTCharacteristicBlueZDBus
from bleak.backends.bluezdbus.descriptor import BleakGATTDescriptorBlueZDBus

from txdbus.client import connect as txdbus_connect
from txdbus.error import RemoteError


logger = logging.getLogger(__name__)


class BleakClientBlueZDBus(BaseBleakClient):
    """A native Linux Bleak Client

    Implemented by using the `BlueZ DBUS API <https://docs.ubuntu.com/core/en/stacks/bluetooth/bluez/docs/reference/dbus-api>`_.

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.

    Keyword Args:
        timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super(BleakClientBlueZDBus, self).__init__(address_or_ble_device, **kwargs)
        self.device = kwargs.get("device") if kwargs.get("device") else "hci0"

        # Backend specific, TXDBus objects and data
        if isinstance(address_or_ble_device, BLEDevice):
            self._device_path = address_or_ble_device.details["path"]
            self._device_info = address_or_ble_device.details.get("props")
        else:
            self._device_path = None
            self._device_info = None
        self._bus = None
        self._reactor = None
        self._rules = {}
        self._subscriptions = list()

        # This maps DBus paths of GATT Characteristics to their BLE handles.
        self._char_path_to_handle = {}

        # We need to know BlueZ version since battery level characteristic
        # are stored in a separate DBus interface in the BlueZ >= 5.48.
        p = subprocess.Popen(["bluetoothctl", "--version"], stdout=subprocess.PIPE)
        out, _ = p.communicate()
        s = re.search(b"(\\d+).(\\d+)", out.strip(b"'"))
        self._bluez_version = tuple(map(int, s.groups()))

    # Connectivity methods

    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        Keyword Args:
            timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

        Returns:
            Boolean representing connection status.

        """
        # A Discover must have been run before connecting to any devices.
        # Find the desired device before trying to connect.
        timeout = kwargs.get("timeout", self._timeout)
        if self._device_path is None:
            device = await BleakScannerBlueZDBus.find_device_by_address(
                self.address, timeout=timeout, device=self.device
            )

            if device:
                self._device_info = device.details.get("props")
                self._device_path = device.details["path"]
            else:
                raise BleakError(
                    "Device with address {0} was not found.".format(self.address)
                )

        loop = asyncio.get_event_loop()
        self._reactor = get_reactor(loop)

        # Create system bus
        self._bus = await txdbus_connect(self._reactor, busAddress="system").asFuture(
            loop
        )

        def _services_resolved_callback(message):
            iface, changed, invalidated = message.body
            is_resolved = defs.DEVICE_INTERFACE and changed.get(
                "ServicesResolved", False
            )
            if iface == is_resolved:
                logger.info("Services resolved for %s", str(self))
                self.services_resolved = True

        rule_id = await signals.listen_properties_changed(
            self._bus, _services_resolved_callback
        )

        logger.debug(
            "Connecting to BLE device @ {0} with {1}".format(self.address, self.device)
        )
        try:
            await self._bus.callRemote(
                self._device_path,
                "Connect",
                interface=defs.DEVICE_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
                timeout=timeout,
            ).asFuture(loop)
        except RemoteError as e:
            await self._cleanup_all()
            if 'Method "Connect" with signature "" on interface' in str(e):
                raise BleakError(
                    "Device with address {0} could not be found. "
                    "Try increasing `timeout` value or moving the device closer.".format(
                        self.address
                    )
                )
            else:
                raise BleakError(str(e))

        if await self.is_connected():
            logger.debug("Connection successful.")
        else:
            await self._cleanup_all()
            raise BleakError(
                "Connection to {0} was not successful!".format(self.address)
            )

        # Get all services. This means making the actual connection.
        await self.get_services()
        properties = await self._get_device_properties()
        if not properties.get("Connected"):
            await self._cleanup_all()
            raise BleakError("Connection failed!")

        await self._bus.delMatch(rule_id).asFuture(loop)
        self._rules["PropChanged"] = await signals.listen_properties_changed(
            self._bus, self._properties_changed_callback
        )
        return True

    async def _cleanup_notifications(self) -> None:
        """
        Remove all pending notifications of the client. This method is used to
        free the DBus matches that have been established.
        """
        for rule_name, rule_id in self._rules.items():
            logger.debug("Removing rule {0}, ID: {1}".format(rule_name, rule_id))
            try:
                await self._bus.delMatch(rule_id).asFuture(asyncio.get_event_loop())
            except Exception as e:
                logger.error(
                    "Could not remove rule {0} ({1}): {2}".format(rule_id, rule_name, e)
                )
        self._rules = {}

        for _uuid in list(self._subscriptions):
            try:
                await self.stop_notify(_uuid)
            except Exception as e:
                logger.error(
                    "Could not remove notifications on characteristic {0}: {1}".format(
                        _uuid, e
                    )
                )
        self._subscriptions = []

    async def _cleanup_dbus_resources(self) -> None:
        """
        Free the resources allocated for both the DBus bus and the Twisted
        reactor. Use this method upon final disconnection.
        """
        # Try to disconnect the System Bus.
        try:
            self._bus.disconnect()
        except Exception as e:
            logger.error("Attempt to disconnect system bus failed: {0}".format(e))
        else:
            # Critical to remove the `self._bus` object here to since it was
            # closed above. If not, calls made to it later could lead to
            # a stuck client.
            self._bus = None

    async def _cleanup_all(self) -> None:
        """
        Free all the allocated resource in DBus and Twisted. Use this method to
        eventually cleanup all otherwise leaked resources.
        """
        self._char_path_to_handle.clear()
        await self._cleanup_notifications()
        await self._cleanup_dbus_resources()

    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        Returns:
            Boolean representing if device is disconnected.

        """
        logger.debug("Disconnecting from BLE device...")
        if self._bus is None:
            # No connection exists. Either one hasn't been created or
            # we have already called disconnect and closed the txdbus
            # connection.
            return True

        # Remove all residual notifications.
        await self._cleanup_notifications()

        # Try to disconnect the actual device/peripheral
        try:
            await self._bus.callRemote(
                self._device_path,
                "Disconnect",
                interface=defs.DEVICE_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
            ).asFuture(asyncio.get_event_loop())
        except Exception as e:
            logger.error("Attempt to disconnect device failed: {0}".format(e))

        is_disconnected = not await self.is_connected()

        await self._cleanup_dbus_resources()

        # Reset all stored services.
        self.services = BleakGATTServiceCollection()

        return is_disconnected

    async def pair(self, *args, **kwargs) -> bool:
        """Pair with the peripheral.

        You can use ConnectDevice method if you already know the MAC address of the device.
        Else you need to StartDiscovery, Trust, Pair and Connect in sequence.

        Returns:
            Boolean regarding success of pairing.

        """
        loop = asyncio.get_event_loop()

        # See if it is already paired.
        is_paired = await self._bus.callRemote(
            self._device_path,
            "Get",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="ss",
            body=[defs.DEVICE_INTERFACE, "Paired"],
            returnSignature="v",
        ).asFuture(asyncio.get_event_loop())
        if is_paired:
            return is_paired

        # Set device as trusted.
        await self._bus.callRemote(
            self._device_path,
            "Set",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="ssv",
            body=[defs.DEVICE_INTERFACE, "Trusted", True],
            returnSignature="",
        ).asFuture(asyncio.get_event_loop())

        logger.debug(
            "Pairing to BLE device @ {0} with {1}".format(self.address, self.device)
        )
        try:
            await self._bus.callRemote(
                self._device_path,
                "Pair",
                interface=defs.DEVICE_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
            ).asFuture(loop)
        except RemoteError as e:
            await self._cleanup_all()
            raise BleakError(
                "Device with address {0} could not be paired with.".format(self.address)
            )

        return await self._bus.callRemote(
            self._device_path,
            "Get",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="ss",
            body=[defs.DEVICE_INTERFACE, "Paired"],
            returnSignature="v",
        ).asFuture(asyncio.get_event_loop())

    async def unpair(self) -> bool:
        """Unpair with the peripheral.

        Returns:
            Boolean regarding success of unpairing.

        """
        warnings.warn(
            "Unpairing is seemingly unavailable in the BlueZ DBus API at the moment."
        )
        return False

    async def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        # TODO: Listen to connected property changes.
        is_connected = False
        try:
            is_connected = await self._bus.callRemote(
                self._device_path,
                "Get",
                interface=defs.PROPERTIES_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
                signature="ss",
                body=[defs.DEVICE_INTERFACE, "Connected"],
                returnSignature="v",
            ).asFuture(asyncio.get_event_loop())
        except AttributeError:
            # The `self._bus` object had already been cleaned up due to disconnect...
            pass
        except ConnectionDone:
            # Twisted error stating that "Connection was closed cleanly."
            pass
        except RemoteError as e:
            if e.errName != "org.freedesktop.DBus.Error.UnknownObject":
                raise
        except Exception as e:
            # Do not want to silence unknown errors. Send this upwards.
            raise
        return is_connected

    # GATT services methods

    async def get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self._services_resolved:
            return self.services

        sleep_loop_sec = 0.02
        total_slept_sec = 0
        services_resolved = False

        while total_slept_sec < 5.0:
            properties = await self._get_device_properties()
            services_resolved = properties.get("ServicesResolved", False)
            if services_resolved:
                break
            await asyncio.sleep(sleep_loop_sec)
            total_slept_sec += sleep_loop_sec

        if not services_resolved:
            raise BleakError("Services discovery error")

        logger.debug("Get Services...")
        objs = await get_managed_objects(self._bus, self._device_path + "/service")

        # There is no guarantee that services are listed before characteristics
        # Managed Objects dict.
        # Need multiple iterations to construct the Service Collection

        _chars, _descs = [], []

        for object_path, interfaces in objs.items():
            logger.debug(utils.format_GATT_object(object_path, interfaces))
            if defs.GATT_SERVICE_INTERFACE in interfaces:
                service = interfaces.get(defs.GATT_SERVICE_INTERFACE)
                self.services.add_service(
                    BleakGATTServiceBlueZDBus(service, object_path)
                )
            elif defs.GATT_CHARACTERISTIC_INTERFACE in interfaces:
                char = interfaces.get(defs.GATT_CHARACTERISTIC_INTERFACE)
                _chars.append([char, object_path])
            elif defs.GATT_DESCRIPTOR_INTERFACE in interfaces:
                desc = interfaces.get(defs.GATT_DESCRIPTOR_INTERFACE)
                _descs.append([desc, object_path])

        for char, object_path in _chars:
            _service = list(filter(lambda x: x.path == char["Service"], self.services))
            self.services.add_characteristic(
                BleakGATTCharacteristicBlueZDBus(char, object_path, _service[0].uuid)
            )

            # D-Bus object path contains handle as last 4 characters of 'charYYYY'
            self._char_path_to_handle[object_path] = int(object_path[-4:], 16)

        for desc, object_path in _descs:
            _characteristic = list(
                filter(
                    lambda x: x.path == desc["Characteristic"],
                    self.services.characteristics.values(),
                )
            )
            self.services.add_descriptor(
                BleakGATTDescriptorBlueZDBus(
                    desc,
                    object_path,
                    _characteristic[0].uuid,
                    int(_characteristic[0].handle),
                )
            )

        self._services_resolved = True
        return self.services

    # IO methods

    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, uuid.UUID],
        **kwargs
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            char_specifier (BleakGATTCharacteristicBlueZDBus, int, str or UUID): The characteristic to read from,
                specified by either integer handle, UUID or directly by the
                BleakGATTCharacteristicBlueZDBus object representing it.

        Returns:
            (bytearray) The read data.

        """
        if not isinstance(char_specifier, BleakGATTCharacteristicBlueZDBus):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier

        if not characteristic:
            # Special handling for BlueZ >= 5.48, where Battery Service (0000180f-0000-1000-8000-00805f9b34fb:)
            # has been moved to interface org.bluez.Battery1 instead of as a regular service.
            if str(char_specifier) == "00002a19-0000-1000-8000-00805f9b34fb" and (
                self._bluez_version[0] == 5 and self._bluez_version[1] >= 48
            ):
                props = await self._get_device_properties(
                    interface=defs.BATTERY_INTERFACE
                )
                # Simulate regular characteristics read to be consistent over all platforms.
                value = bytearray([props.get("Percentage", "")])
                logger.debug(
                    "Read Battery Level {0} | {1}: {2}".format(
                        char_specifier, self._device_path, value
                    )
                )
                return value
            if str(char_specifier) == "00002a00-0000-1000-8000-00805f9b34fb" and (
                self._bluez_version[0] == 5 and self._bluez_version[1] >= 48
            ):
                props = await self._get_device_properties(
                    interface=defs.DEVICE_INTERFACE
                )
                # Simulate regular characteristics read to be consistent over all platforms.
                value = bytearray(props.get("Name", "").encode("ascii"))
                logger.debug(
                    "Read Device Name {0} | {1}: {2}".format(
                        char_specifier, self._device_path, value
                    )
                )
                return value

            raise BleakError(
                "Characteristic with UUID {0} could not be found!".format(
                    char_specifier
                )
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
            ).asFuture(asyncio.get_event_loop())
        )

        logger.debug(
            "Read Characteristic {0} | {1}: {2}".format(
                characteristic.uuid, characteristic.path, value
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
            raise BleakError("Descriptor with handle {0} was not found!".format(handle))

        value = bytearray(
            await self._bus.callRemote(
                descriptor.path,
                "ReadValue",
                interface=defs.GATT_DESCRIPTOR_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
                signature="a{sv}",
                body=[{}],
                returnSignature="ay",
            ).asFuture(asyncio.get_event_loop())
        )

        logger.debug(
            "Read Descriptor {0} | {1}: {2}".format(handle, descriptor.path, value)
        )
        return value

    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, uuid.UUID],
        data: bytearray,
        response: bool = False,
    ) -> None:
        """Perform a write operation on the specified GATT characteristic.

        .. note::

            The version check below is for the "type" option to the
            "Characteristic.WriteValue" method that was added to `Bluez in 5.51
            <https://git.kernel.org/pub/scm/bluetooth/bluez.git/commit?id=fa9473bcc48417d69cc9ef81d41a72b18e34a55a>`_
            Before that commit, ``Characteristic.WriteValue`` was only "Write with
            response". ``Characteristic.AcquireWrite`` was `added in Bluez 5.46
            <https://git.kernel.org/pub/scm/bluetooth/bluez.git/commit/doc/gatt-api.txt?id=f59f3dedb2c79a75e51a3a0d27e2ae06fefc603e>`_
            which can be used to "Write without response", but for older versions
            of Bluez, it is not possible to "Write without response".

        Args:
            char_specifier (BleakGATTCharacteristicBlueZDBus, int, str or UUID): The characteristic to write
                to, specified by either integer handle, UUID or directly by the
                BleakGATTCharacteristicBlueZDBus object representing it.
            data (bytes or bytearray): The data to send.
            response (bool): If write-with-response operation should be done. Defaults to `False`.

        """
        if not isinstance(char_specifier, BleakGATTCharacteristicBlueZDBus):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier

        if not characteristic:
            raise BleakError("Characteristic {0} was not found!".format(char_specifier))
        if (
            "write" not in characteristic.properties
            and "write-without-response" not in characteristic.properties
        ):
            raise BleakError(
                "Characteristic %s does not support write operations!"
                % str(characteristic.uuid)
            )
        if not response and "write-without-response" not in characteristic.properties:
            response = True
            # Force response here, since the device only supports that.
        if (
            response
            and "write" not in characteristic.properties
            and "write-without-response" in characteristic.properties
        ):
            response = False
            logger.warning(
                "Characteristic %s does not support Write with response. Trying without..."
                % str(characteristic.uuid)
            )

        # See docstring for details about this handling.
        if not response and self._bluez_version[0] == 5 and self._bluez_version[1] < 46:
            raise BleakError("Write without response requires at least BlueZ 5.46")
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
            ).asFuture(asyncio.get_event_loop())
        else:
            # Older versions of BlueZ don't have the "type" option, so we have
            # to write the hard way. This isn't the most efficient way of doing
            # things, but it works.
            fd, _ = await self._bus.callRemote(
                characteristic.path,
                "AcquireWrite",
                interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                destination=defs.BLUEZ_SERVICE,
                signature="a{sv}",
                body=[{}],
                returnSignature="hq",
            ).asFuture(asyncio.get_event_loop())
            os.write(fd, data)
            os.close(fd)

        logger.debug(
            "Write Characteristic {0} | {1}: {2}".format(
                characteristic.uuid, characteristic.path, data
            )
        )

    async def write_gatt_descriptor(self, handle: int, data: bytearray) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            data (bytes or bytearray): The data to send.

        """
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor with handle {0} was not found!".format(handle))
        await self._bus.callRemote(
            descriptor.path,
            "WriteValue",
            interface=defs.GATT_DESCRIPTOR_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="aya{sv}",
            body=[data, {"type": "command"}],
            returnSignature="",
        ).asFuture(asyncio.get_event_loop())

        logger.debug(
            "Write Descriptor {0} | {1}: {2}".format(handle, descriptor.path, data)
        )

    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, uuid.UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs
    ) -> None:
        """Activate notifications/indications on a characteristic.

        Callbacks must accept two inputs. The first will be a integer handle of the characteristic generating the
        data and the second will be a ``bytearray`` containing the data sent from the connected server.

        .. code-block:: python

            def callback(sender: int, data: bytearray):
                print(f"{sender}: {data}")
            client.start_notify(char_uuid, callback)

        Args:
            char_specifier (BleakGATTCharacteristicBlueZDBus, int, str or UUID): The characteristic to activate
                notifications/indications on a characteristic, specified by either integer handle,
                UUID or directly by the BleakGATTCharacteristicBlueZDBus object representing it.
            callback (function): The function to be called on notification.

        Keyword Args:
            notification_wrapper (bool): Set to `False` to avoid parsing of
                notification to bytearray.

        """
        _wrap = kwargs.get("notification_wrapper", True)
        if not isinstance(char_specifier, BleakGATTCharacteristicBlueZDBus):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier

        if not characteristic:
            # Special handling for BlueZ >= 5.48, where Battery Service (0000180f-0000-1000-8000-00805f9b34fb:)
            # has been moved to interface org.bluez.Battery1 instead of as a regular service.
            # The org.bluez.Battery1 on the other hand does not provide a notification method, so here we cannot
            # provide this functionality...
            # See https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/refs/tags/5.48/doc/battery-api.txt
            if str(char_specifier) == "00002a19-0000-1000-8000-00805f9b34fb" and (
                self._bluez_version[0] == 5 and self._bluez_version[1] >= 48
            ):
                raise BleakError(
                    "Notifications on Battery Level Char ({0}) is not "
                    "possible in BlueZ >= 5.48. Use regular read instead.".format(
                        char_specifier
                    )
                )
            raise BleakError(
                "Characteristic with UUID {0} could not be found!".format(
                    char_specifier
                )
            )
        await self._bus.callRemote(
            characteristic.path,
            "StartNotify",
            interface=defs.GATT_CHARACTERISTIC_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="",
            body=[],
            returnSignature="",
        ).asFuture(asyncio.get_event_loop())

        if _wrap:
            self._notification_callbacks[
                characteristic.path
            ] = _data_notification_wrapper(
                callback, self._char_path_to_handle
            )  # noqa | E123 error in flake8...
        else:
            self._notification_callbacks[
                characteristic.path
            ] = _regular_notification_wrapper(
                callback, self._char_path_to_handle
            )  # noqa | E123 error in flake8...

        self._subscriptions.append(characteristic.handle)

    async def stop_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, uuid.UUID],
    ) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            char_specifier (BleakGATTCharacteristicBlueZDBus, int, str or UUID): The characteristic to deactivate
                notification/indication on, specified by either integer handle, UUID or
                directly by the BleakGATTCharacteristicBlueZDBus object representing it.

        """
        if not isinstance(char_specifier, BleakGATTCharacteristicBlueZDBus):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} not found!".format(char_specifier))

        await self._bus.callRemote(
            characteristic.path,
            "StopNotify",
            interface=defs.GATT_CHARACTERISTIC_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="",
            body=[],
            returnSignature="",
        ).asFuture(asyncio.get_event_loop())
        self._notification_callbacks.pop(characteristic.path, None)

        self._subscriptions.remove(characteristic.handle)

    # DBUS introspection method for characteristics.

    async def get_all_for_characteristic(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, uuid.UUID],
    ) -> dict:
        """Get all properties for a characteristic.

        This method should generally not be needed by end user, since it is a DBus specific method.

        Args:
            char_specifier: The characteristic to get properties for, specified by either
                integer handle, UUID or directly by the BleakGATTCharacteristicBlueZDBus
                object representing it.

        Returns:
            (dict) Properties dictionary

        """
        if not isinstance(char_specifier, BleakGATTCharacteristicBlueZDBus):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} not found!".format(char_specifier))

        out = await self._bus.callRemote(
            characteristic.path,
            "GetAll",
            interface=defs.PROPERTIES_INTERFACE,
            destination=defs.BLUEZ_SERVICE,
            signature="s",
            body=[defs.GATT_CHARACTERISTIC_INTERFACE],
            returnSignature="a{sv}",
        ).asFuture(asyncio.get_event_loop())
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
        ).asFuture(asyncio.get_event_loop())

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

        logger.debug(
            "DBUS: path: {}, domain: {}, body: {}".format(
                message.path, message.body[0], message.body[1]
            )
        )

        if message.body[0] == defs.GATT_CHARACTERISTIC_INTERFACE:
            if message.path in self._notification_callbacks:
                logger.debug(
                    "GATT Char Properties Changed: {0} | {1}".format(
                        message.path, message.body[1:]
                    )
                )
                self._notification_callbacks[message.path](
                    message.path, message.body[1]
                )
        elif message.body[0] == defs.DEVICE_INTERFACE:
            device_path = "/org/bluez/%s/dev_%s" % (
                self.device,
                self.address.replace(":", "_"),
            )
            if message.path.lower() == device_path.lower():
                message_body_map = message.body[1]
                if (
                    "Connected" in message_body_map
                    and not message_body_map["Connected"]
                ):
                    logger.debug("Device {} disconnected.".format(self.address))

                    task = asyncio.get_event_loop().create_task(self._cleanup_all())
                    if self._disconnected_callback is not None:
                        task.add_done_callback(
                            partial(self._disconnected_callback, self)
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
