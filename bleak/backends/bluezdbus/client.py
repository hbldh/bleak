# -*- coding: utf-8 -*-
"""
BLE Client for BlueZ on Linux
"""
import inspect
import logging
import asyncio
import os
import re
import subprocess
import warnings
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType, ErrorType, MessageType
from dbus_next.message import Message
from dbus_next.signature import Variant

from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.characteristic import BleakGATTCharacteristicBlueZDBus
from bleak.backends.bluezdbus.descriptor import BleakGATTDescriptorBlueZDBus
from bleak.backends.bluezdbus.scanner import BleakScannerBlueZDBus
from bleak.backends.bluezdbus.service import BleakGATTServiceBlueZDBus
from bleak.backends.bluezdbus.signals import MatchRules, add_match, remove_match
from bleak.backends.bluezdbus.utils import (
    assert_reply,
    extract_service_handle_from_path,
    unpack_variants,
)
from bleak.backends.client import BaseBleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.exc import BleakDBusError, BleakError


logger = logging.getLogger(__name__)


class BleakClientBlueZDBus(BaseBleakClient):
    """A native Linux Bleak Client

    Implemented by using the `BlueZ DBUS API <https://docs.ubuntu.com/core/en/stacks/bluetooth/bluez/docs/reference/dbus-api>`_.

    Args:
        address_or_ble_device (`BLEDevice` or str): The Bluetooth address of the BLE peripheral to connect to or the `BLEDevice` object representing it.

    Keyword Args:
        timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.
        disconnected_callback (callable): Callback that will be scheduled in the
            event loop when the client is disconnected. The callable must take one
            argument, which will be this client object.
        adapter (str): Bluetooth adapter to use for discovery.
    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super(BleakClientBlueZDBus, self).__init__(address_or_ble_device, **kwargs)
        # kwarg "device" is for backwards compatibility
        self._adapter = kwargs.get("adapter", kwargs.get("device", "hci0"))

        # Backend specific, D-Bus objects and data
        if isinstance(address_or_ble_device, BLEDevice):
            self._device_path = address_or_ble_device.details["path"]
            self._device_info = address_or_ble_device.details.get("props")
        else:
            self._device_path = None
            self._device_info = None

        # D-Bus message bus
        self._bus: Optional[MessageBus] = None
        # match rules we are subscribed to that need to be removed on disconnect
        self._rules: List[MatchRules] = []
        # D-Bus properties for the device
        self._properties: Dict[str, Any] = {}
        # list of characteristic handles that have notifications enabled
        self._subscriptions: List[int] = []
        # provides synchronization between get_services() and PropertiesChanged signal
        self._services_resolved_event: Optional[asyncio.Event] = None
        # indicates disconnect request in progress when not None
        self._disconnecting_event: Optional[asyncio.Event] = None
        # used to ensure device gets disconnected if event loop crashes
        self._disconnect_monitor_event: Optional[asyncio.Event] = None

        # used to override mtu_size property
        self._mtu_size: Optional[int] = None

        # get BlueZ version
        p = subprocess.Popen(["bluetoothctl", "--version"], stdout=subprocess.PIPE)
        out, _ = p.communicate()
        s = re.search(b"(\\d+).(\\d+)", out.strip(b"'"))
        bluez_version = tuple(map(int, s.groups()))

        # BlueZ version features
        self._can_write_without_response = (
            bluez_version[0] == 5 and bluez_version[1] >= 46
        )
        self._write_without_response_workaround_needed = (
            bluez_version[0] == 5 and bluez_version[1] < 51
        )
        self._hides_battery_characteristic = self._hides_device_name_characteristic = (
            bluez_version[0] == 5 and bluez_version[1] >= 48
        )

    # Connectivity methods

    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        Keyword Args:
            timeout (float): Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.

        Returns:
            Boolean representing connection status.

        Raises:
            BleakError: If the device is already connected or if the device could not be found.
            BleakDBusError: If there was a D-Bus error
            asyncio.TimeoutError: If the connection timed out
        """
        logger.debug(f"Connecting to device @ {self.address} with {self._adapter}")

        if self.is_connected:
            raise BleakError("Client is already connected")

        # A Discover must have been run before connecting to any devices.
        # Find the desired device before trying to connect.
        timeout = kwargs.get("timeout", self._timeout)
        if self._device_path is None:
            device = await BleakScannerBlueZDBus.find_device_by_address(
                self.address, timeout=timeout, adapter=self._adapter
            )

            if device:
                self._device_info = device.details.get("props")
                self._device_path = device.details["path"]
            else:
                raise BleakError(
                    "Device with address {0} was not found.".format(self.address)
                )

        # Create system bus
        self._bus = await MessageBus(
            bus_type=BusType.SYSTEM, negotiate_unix_fd=True
        ).connect()

        try:
            # Add signal handlers. These monitor the device D-Bus object and
            # all of its descendats (services, characteristics, descriptors).
            # This we always have an up-to-date state for all of these that is
            # maintained automatically in the background.

            self._bus.add_message_handler(self._parse_msg)

            rules = MatchRules(
                interface=defs.OBJECT_MANAGER_INTERFACE,
                member="InterfacesAdded",
                arg0path=f"{self._device_path}/",
            )
            reply = await add_match(self._bus, rules)
            assert_reply(reply)
            self._rules.append(rules)

            rules = MatchRules(
                interface=defs.OBJECT_MANAGER_INTERFACE,
                member="InterfacesRemoved",
                arg0path=f"{self._device_path}/",
            )
            reply = await add_match(self._bus, rules)
            assert_reply(reply)
            self._rules.append(rules)

            rules = MatchRules(
                interface=defs.PROPERTIES_INTERFACE,
                member="PropertiesChanged",
                path_namespace=self._device_path,
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

            interfaces_and_props: Dict[str, Dict[str, Variant]] = reply.body[0]

            # The device may have been removed from BlueZ since the time we stopped scanning
            if self._device_path not in interfaces_and_props:
                # Sometimes devices can be removed from the BlueZ object manager
                # before we connect to them. In this case we try using the
                # org.bluez.Adapter1.ConnectDevice method instead. This method
                # requires that bluetoothd is run with the --experimental flag
                # and is available since BlueZ 5.49.
                logger.debug(
                    f"org.bluez.Device1 object not found, trying org.bluez.Adapter1.ConnectDevice ({self._device_path})"
                )
                reply = await asyncio.wait_for(
                    self._bus.call(
                        Message(
                            destination=defs.BLUEZ_SERVICE,
                            interface=defs.ADAPTER_INTERFACE,
                            path=f"/org/bluez/{self._adapter}",
                            member="ConnectDevice",
                            signature="a{sv}",
                            body=[
                                {
                                    "Address": Variant(
                                        "s", self._device_info["Address"]
                                    ),
                                    "AddressType": Variant(
                                        "s", self._device_info["AddressType"]
                                    ),
                                }
                            ],
                        )
                    ),
                    timeout,
                )

                # FIXME: how to cancel connection if timeout?

                if (
                    reply.message_type == MessageType.ERROR
                    and reply.error_name == ErrorType.UNKNOWN_METHOD.value
                ):
                    logger.debug(
                        f"org.bluez.Adapter1.ConnectDevice not found ({self._device_path}), try enabling bluetoothd --experimental"
                    )
                    raise BleakError(
                        "Device with address {0} could not be found. "
                        "Try increasing `timeout` value or moving the device closer.".format(
                            self.address
                        )
                    )

                assert_reply(reply)
            else:
                # required interface
                self._properties = unpack_variants(
                    interfaces_and_props[self._device_path][defs.DEVICE_INTERFACE]
                )

                # optional interfaces - services and characteristics may not
                # be populated yet
                for path, interfaces in interfaces_and_props.items():
                    if not path.startswith(self._device_path):
                        continue

                    if defs.GATT_SERVICE_INTERFACE in interfaces:
                        obj = unpack_variants(interfaces[defs.GATT_SERVICE_INTERFACE])
                        self.services.add_service(BleakGATTServiceBlueZDBus(obj, path))

                    if defs.GATT_CHARACTERISTIC_INTERFACE in interfaces:
                        obj = unpack_variants(
                            interfaces[defs.GATT_CHARACTERISTIC_INTERFACE]
                        )
                        service = interfaces_and_props[obj["Service"]][
                            defs.GATT_SERVICE_INTERFACE
                        ]
                        uuid = service["UUID"].value
                        handle = extract_service_handle_from_path(obj["Service"])
                        self.services.add_characteristic(
                            BleakGATTCharacteristicBlueZDBus(obj, path, uuid, handle)
                        )

                    if defs.GATT_DESCRIPTOR_INTERFACE in interfaces:
                        obj = unpack_variants(
                            interfaces[defs.GATT_DESCRIPTOR_INTERFACE]
                        )
                        characteristic = interfaces_and_props[obj["Characteristic"]][
                            defs.GATT_CHARACTERISTIC_INTERFACE
                        ]
                        uuid = characteristic["UUID"].value
                        handle = extract_service_handle_from_path(obj["Characteristic"])
                        self.services.add_descriptor(
                            BleakGATTDescriptorBlueZDBus(obj, path, uuid, handle)
                        )

                try:
                    reply = await asyncio.wait_for(
                        self._bus.call(
                            Message(
                                destination=defs.BLUEZ_SERVICE,
                                interface=defs.DEVICE_INTERFACE,
                                path=self._device_path,
                                member="Connect",
                            )
                        ),
                        timeout,
                    )
                    assert_reply(reply)
                except BaseException:
                    # calling Disconnect cancels any pending connect request
                    try:
                        reply = await self._bus.call(
                            Message(
                                destination=defs.BLUEZ_SERVICE,
                                interface=defs.DEVICE_INTERFACE,
                                path=self._device_path,
                                member="Disconnect",
                            )
                        )
                        try:
                            assert_reply(reply)
                        except BleakDBusError as e:
                            # if the object no longer exists, then we know we
                            # are disconnected for sure, so don't need to log a
                            # warning about it
                            if e.dbus_error != ErrorType.UNKNOWN_OBJECT.value:
                                raise
                    except Exception as e:
                        logger.warning(
                            f"Failed to cancel connection ({self._device_path}): {e}"
                        )

                    raise

            if self.is_connected:
                logger.debug(f"Connection successful ({self._device_path})")
            else:
                raise BleakError(
                    f"Connection was not successful! ({self._device_path})"
                )

            # Create a task that runs until the device is disconnected.
            self._disconnect_monitor_event = asyncio.Event()
            asyncio.ensure_future(self._disconnect_monitor())

            # Get all services. This means making the actual connection.
            await self.get_services()

            return True
        except BaseException:
            await self._cleanup_all()
            raise

    async def _disconnect_monitor(self) -> None:
        # This task runs until the device is disconnected. If the task is
        # cancelled, it probably means that the event loop crashed so we
        # try to disconnected the device. Otherwise BlueZ will keep the device
        # connected even after Python exits. This will only work if the event
        # loop is called with asyncio.run() or otherwise runs pending tasks
        # after the original event loop stops. This will also cause an exception
        # if a run loop is stopped before the device is disconnected since this
        # task will still be running and asyncio compains if a loop with running
        # tasks is stopped.
        try:
            await self._disconnect_monitor_event.wait()
        except asyncio.CancelledError:
            try:
                # by using send() instead of call(), we ensure that the message
                # gets sent, but we don't wait for a reply, which could take
                # over one second while the device disconnects.
                await self._bus.send(
                    Message(
                        destination=defs.BLUEZ_SERVICE,
                        path=self._device_path,
                        interface=defs.DEVICE_INTERFACE,
                        member="Disconnect",
                    )
                )
            except Exception:
                pass

    async def _remove_signal_handlers(self) -> None:
        """
        Remove all pending notifications of the client. This method is used to
        free the DBus matches that have been established.
        """
        logger.debug(f"_remove_signal_handlers({self._device_path})")

        if self._bus is None:
            logger.debug("no bus object")
            return

        self._bus.remove_message_handler(self._parse_msg)

        # avoid reentrancy issues by taking a copy of self._rules
        old_rules, self._rules = self._rules, []
        for rule in old_rules:
            try:
                await remove_match(self._bus, rule)
            except Exception as e:
                logger.error(
                    f"Failed to remove match {rule.member} ({self._device_path}): {e}"
                )

        # There is no need to call stop_notify() here since the the device is
        # already disconnected and we are about to close the D-Bus message bus
        # which has the effect of clearing all notifications in BlueZ.
        self._subscriptions = []

    def _disconnect_message_bus(self) -> None:
        """
        Free the resources allocated for both the DBus bus.
        Use this method upon final disconnection.
        """
        logger.debug(f"_disconnect_message_bus({self._device_path})")

        if not self._bus:
            logger.debug(f"already disconnected ({self._device_path})")
            return

        # Try to disconnect the System Bus.
        try:
            self._bus.disconnect()
        except Exception as e:
            logger.error(
                f"Attempt to disconnect system bus failed ({self._device_path}): {e}"
            )
        else:
            # Critical to remove the `self._bus` object here to since it was
            # closed above. If not, calls made to it later could lead to
            # a stuck client.
            self._bus = None

    async def _cleanup_all(self) -> None:
        """
        Free all the allocated resource in DBus. Use this method to
        eventually cleanup all otherwise leaked resources.
        """
        await self._remove_signal_handlers()
        self._disconnect_message_bus()

    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        Returns:
            Boolean representing if device is disconnected.

        Raises:
            BleakDBusError: If there was a D-Bus error
            asyncio.TimeoutError if the device was not disconnected within 10 seconds
        """
        logger.debug(f"Disconnecting ({self._device_path})")

        if self._bus is None:
            # No connection exists. Either one hasn't been created or
            # we have already called disconnect and closed the D-Bus
            # connection.
            logger.debug(f"already disconnected ({self._device_path})")
            return True

        if self._disconnecting_event:
            # another call to disconnect() is already in progress
            logger.debug(f"already in progress ({self._device_path})")
            await asyncio.wait_for(self._disconnecting_event.wait(), timeout=10)
        elif self.is_connected:
            self._disconnecting_event = asyncio.Event()
            try:
                # Try to disconnect the actual device/peripheral
                reply = await self._bus.call(
                    Message(
                        destination=defs.BLUEZ_SERVICE,
                        path=self._device_path,
                        interface=defs.DEVICE_INTERFACE,
                        member="Disconnect",
                    )
                )
                assert_reply(reply)
                await asyncio.wait_for(self._disconnecting_event.wait(), timeout=10)
            finally:
                self._disconnecting_event = None

        # sanity check to make sure _cleanup_all() was triggered by the
        # "PropertiesChanged" signal handler and that it completed successfully
        assert self._bus is None

        # Reset all stored services.
        self.services = BleakGATTServiceCollection()
        self._services_resolved = False

        return True

    async def pair(self, *args, **kwargs) -> bool:
        """Pair with the peripheral.

        You can use ConnectDevice method if you already know the MAC address of the device.
        Else you need to StartDiscovery, Trust, Pair and Connect in sequence.

        Returns:
            Boolean regarding success of pairing.

        """
        # See if it is already paired.
        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._device_path,
                interface=defs.PROPERTIES_INTERFACE,
                member="Get",
                signature="ss",
                body=[defs.DEVICE_INTERFACE, "Paired"],
            )
        )
        assert_reply(reply)
        if reply.body[0].value:
            logger.debug(
                f"BLE device @ {self.address} already paired with {self._adapter}"
            )
            return True

        # Set device as trusted.
        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._device_path,
                interface=defs.PROPERTIES_INTERFACE,
                member="Set",
                signature="ssv",
                body=[defs.DEVICE_INTERFACE, "Trusted", Variant("b", True)],
            )
        )
        assert_reply(reply)

        logger.debug(
            "Pairing to BLE device @ {0} with {1}".format(self.address, self._adapter)
        )

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._device_path,
                interface=defs.DEVICE_INTERFACE,
                member="Pair",
            )
        )
        assert_reply(reply)

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=self._device_path,
                interface=defs.PROPERTIES_INTERFACE,
                member="Get",
                signature="ss",
                body=[defs.DEVICE_INTERFACE, "Paired"],
            )
        )
        assert_reply(reply)

        return reply.body[0].value

    async def unpair(self) -> bool:
        """Unpair with the peripheral.

        Returns:
            Boolean regarding success of unpairing.

        """
        warnings.warn(
            "Unpairing is seemingly unavailable in the BlueZ DBus API at the moment."
        )
        return False

    @property
    def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        return self._DeprecatedIsConnectedReturn(
            False if self._bus is None else self._properties.get("Connected", False)
        )

    async def _acquire_mtu(self) -> None:
        """Acquires the MTU for this device by calling the "AcquireWrite" or
        "AcquireNotify" method of the first characteristic that has such a method.

        This method only needs to be called once, after connecting to the device
        but before accessing the ``mtu_size`` property.

        If a device uses encryption on characteristics, it will need to be bonded
        first before calling this method.
        """
        # This will try to get the "best" characteristic for getting the MTU.
        # We would rather not start notifications if we don't have to.
        try:
            method = "AcquireWrite"
            char = next(
                c
                for c in self.services.characteristics.values()
                if "write-without-response" in c.properties
            )
        except StopIteration:
            method = "AcquireNotify"
            char = next(
                c
                for c in self.services.characteristics.values()
                if "notify" in c.properties
            )

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=char.path,
                interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                member=method,
                signature="a{sv}",
                body=[{}],
            )
        )
        assert_reply(reply)

        # we aren't actually using the write or notify, we just want the MTU
        os.close(reply.unix_fds[0])
        self._mtu_size = reply.body[1]

    @property
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection"""
        if self._mtu_size is None:
            warnings.warn(
                "Using default MTU value. Call _assign_mtu() or set _mtu_size first to avoid this warning."
            )
            return 23

        return self._mtu_size

    # GATT services methods

    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if not self.is_connected:
            raise BleakError("Not connected")

        if self._services_resolved:
            return self.services

        if not self._properties["ServicesResolved"]:
            logger.debug(f"Waiting for ServicesResolved ({self._device_path})")
            self._services_resolved_event = asyncio.Event()
            try:
                await asyncio.wait_for(self._services_resolved_event.wait(), 5)
            finally:
                self._services_resolved_event = None

        self._services_resolved = True
        return self.services

    # IO methods

    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, UUID],
        **kwargs,
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            char_specifier (BleakGATTCharacteristicBlueZDBus, int, str or UUID): The characteristic to read from,
                specified by either integer handle, UUID or directly by the
                BleakGATTCharacteristicBlueZDBus object representing it.

        Returns:
            (bytearray) The read data.

        """
        if not self.is_connected:
            raise BleakError("Not connected")

        if not isinstance(char_specifier, BleakGATTCharacteristicBlueZDBus):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier

        if not characteristic:
            # Special handling for BlueZ >= 5.48, where Battery Service (0000180f-0000-1000-8000-00805f9b34fb:)
            # has been moved to interface org.bluez.Battery1 instead of as a regular service.
            if str(char_specifier) == "00002a19-0000-1000-8000-00805f9b34fb" and (
                self._hides_battery_characteristic
            ):
                reply = await self._bus.call(
                    Message(
                        destination=defs.BLUEZ_SERVICE,
                        path=self._device_path,
                        interface=defs.PROPERTIES_INTERFACE,
                        member="GetAll",
                        signature="s",
                        body=[defs.BATTERY_INTERFACE],
                    )
                )
                assert_reply(reply)
                # Simulate regular characteristics read to be consistent over all platforms.
                value = bytearray(reply.body[0]["Percentage"].value)
                logger.debug(
                    "Read Battery Level {0} | {1}: {2}".format(
                        char_specifier, self._device_path, value
                    )
                )
                return value
            if str(char_specifier) == "00002a00-0000-1000-8000-00805f9b34fb" and (
                self._hides_device_name_characteristic
            ):
                # Simulate regular characteristics read to be consistent over all platforms.
                value = bytearray(self._properties["Name"].encode("ascii"))
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

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=characteristic.path,
                interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                member="ReadValue",
                signature="a{sv}",
                body=[{}],
            )
        )
        assert_reply(reply)
        value = bytearray(reply.body[0])

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
        if not self.is_connected:
            raise BleakError("Not connected")

        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor with handle {0} was not found!".format(handle))

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=descriptor.path,
                interface=defs.GATT_DESCRIPTOR_INTERFACE,
                member="ReadValue",
                signature="a{sv}",
                body=[{}],
            )
        )
        assert_reply(reply)
        value = bytearray(reply.body[0])

        logger.debug(
            "Read Descriptor {0} | {1}: {2}".format(handle, descriptor.path, value)
        )
        return value

    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, UUID],
        data: Union[bytes, bytearray, memoryview],
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
        if not self.is_connected:
            raise BleakError("Not connected")

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
        if not response and not self._can_write_without_response:
            raise BleakError("Write without response requires at least BlueZ 5.46")
        if response or not self._write_without_response_workaround_needed:
            # TODO: Add OnValueUpdated handler for response=True?
            reply = await self._bus.call(
                Message(
                    destination=defs.BLUEZ_SERVICE,
                    path=characteristic.path,
                    interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                    member="WriteValue",
                    signature="aya{sv}",
                    body=[
                        bytes(data),
                        {"type": Variant("s", "request" if response else "command")},
                    ],
                )
            )
            assert_reply(reply)
        else:
            # Older versions of BlueZ don't have the "type" option, so we have
            # to write the hard way. This isn't the most efficient way of doing
            # things, but it works.
            reply = await self._bus.call(
                Message(
                    destination=defs.BLUEZ_SERVICE,
                    path=characteristic.path,
                    interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                    member="AcquireWrite",
                    signature="a{sv}",
                    body=[{}],
                )
            )
            assert_reply(reply)
            fd = reply.unix_fds[0]
            try:
                os.write(fd, data)
            finally:
                os.close(fd)

        logger.debug(
            "Write Characteristic {0} | {1}: {2}".format(
                characteristic.uuid, characteristic.path, data
            )
        )

    async def write_gatt_descriptor(
        self, handle: int, data: Union[bytes, bytearray, memoryview]
    ) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            handle (int): The handle of the descriptor to read from.
            data (bytes or bytearray): The data to send.

        """
        if not self.is_connected:
            raise BleakError("Not connected")

        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor with handle {0} was not found!".format(handle))

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=descriptor.path,
                interface=defs.GATT_DESCRIPTOR_INTERFACE,
                member="WriteValue",
                signature="aya{sv}",
                body=[bytes(data), {"type": Variant("s", "command")}],
            )
        )
        assert_reply(reply)

        logger.debug(
            "Write Descriptor {0} | {1}: {2}".format(handle, descriptor.path, data)
        )

    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs,
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
        """
        if not self.is_connected:
            raise BleakError("Not connected")

        if inspect.iscoroutinefunction(callback):

            def bleak_callback(s, d):
                asyncio.ensure_future(callback(s, d))

        else:
            bleak_callback = callback

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
                self._hides_battery_characteristic
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

        self._notification_callbacks[characteristic.path] = bleak_callback
        self._subscriptions.append(characteristic.handle)

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=characteristic.path,
                interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                member="StartNotify",
            )
        )
        assert_reply(reply)

    async def stop_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristicBlueZDBus, int, str, UUID],
    ) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            char_specifier (BleakGATTCharacteristicBlueZDBus, int, str or UUID): The characteristic to deactivate
                notification/indication on, specified by either integer handle, UUID or
                directly by the BleakGATTCharacteristicBlueZDBus object representing it.

        """
        if not self.is_connected:
            raise BleakError("Not connected")

        if not isinstance(char_specifier, BleakGATTCharacteristicBlueZDBus):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} not found!".format(char_specifier))

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path=characteristic.path,
                interface=defs.GATT_CHARACTERISTIC_INTERFACE,
                member="StopNotify",
            )
        )
        assert_reply(reply)

        self._notification_callbacks.pop(characteristic.path, None)
        try:
            self._subscriptions.remove(characteristic.handle)
        except ValueError:
            pass

    # Internal Callbacks

    def _parse_msg(self, message: Message):
        if message.message_type != MessageType.SIGNAL:
            return

        logger.debug(
            "received D-Bus signal: {0}.{1} ({2}): {3}".format(
                message.interface, message.member, message.path, message.body
            )
        )

        if message.member == "InterfacesAdded":
            path, interfaces = message.body

            if defs.GATT_SERVICE_INTERFACE in interfaces:
                obj = unpack_variants(interfaces[defs.GATT_SERVICE_INTERFACE])
                # if this assert fails, it means our match rules are probably wrong
                assert obj["Device"] == self._device_path
                self.services.add_service(BleakGATTServiceBlueZDBus(obj, path))

            if defs.GATT_CHARACTERISTIC_INTERFACE in interfaces:
                obj = unpack_variants(interfaces[defs.GATT_CHARACTERISTIC_INTERFACE])
                service = next(
                    x
                    for x in self.services.services.values()
                    if x.path == obj["Service"]
                )
                self.services.add_characteristic(
                    BleakGATTCharacteristicBlueZDBus(
                        obj, path, service.uuid, service.handle
                    )
                )

            if defs.GATT_DESCRIPTOR_INTERFACE in interfaces:
                obj = unpack_variants(interfaces[defs.GATT_DESCRIPTOR_INTERFACE])
                handle = extract_service_handle_from_path(obj["Characteristic"])
                characteristic = self.services.characteristics[handle]
                self.services.add_descriptor(
                    BleakGATTDescriptorBlueZDBus(obj, path, characteristic.uuid, handle)
                )
        elif message.member == "InterfacesRemoved":
            path, interfaces = message.body

        elif message.member == "PropertiesChanged":
            interface, changed, _ = message.body
            changed = unpack_variants(changed)

            if interface == defs.GATT_CHARACTERISTIC_INTERFACE:
                if message.path in self._notification_callbacks and "Value" in changed:
                    handle = extract_service_handle_from_path(message.path)
                    self._notification_callbacks[message.path](
                        handle, bytearray(changed["Value"])
                    )
            elif interface == defs.DEVICE_INTERFACE:
                self._properties.update(changed)

                if "ServicesResolved" in changed:
                    if changed["ServicesResolved"]:
                        if self._services_resolved_event:
                            self._services_resolved_event.set()
                    else:
                        self._services_resolved = False

                if "Connected" in changed and not changed["Connected"]:
                    logger.debug(f"Device disconnected ({self._device_path})")

                    if self._disconnect_monitor_event:
                        self._disconnect_monitor_event.set()
                        self._disconnect_monitor_event = None

                    task = asyncio.ensure_future(self._cleanup_all())
                    if self._disconnected_callback is not None:
                        task.add_done_callback(
                            lambda _: self._disconnected_callback(self)
                        )
                    disconnecting_event = self._disconnecting_event
                    if disconnecting_event:
                        task.add_done_callback(lambda _: disconnecting_event.set())
