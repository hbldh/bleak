from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import asyncio
import dataclasses
import logging
import uuid
from typing import Any, Optional, Union, cast

from android.bluetooth import (
    BluetoothAdapter,
    BluetoothDevice,
    BluetoothGatt,
    BluetoothGattCharacteristic,
    BluetoothGattDescriptor,
    BluetoothGattService,
    BluetoothProfile,
)
from android.content import Context, Intent
from android.os import Build
from java import jbyte
from java.chaquopy import jarray
from java.util import UUID

from bleak._compat import override
from bleak.args import SizedBuffer
from bleak.assigned_numbers import gatt_char_props_to_strs
from bleak.backends.android.broadcast import BroadcastReceiver
from bleak.backends.android.client_callback import (
    OnCharacteristicReadCallback,
    OnCharacteristicWriteCallback,
    OnConnectionStateChangeCallback,
    OnConnectionStateChangeResult,
    OnDescriptorReadCallback,
    OnDescriptorWriteCallback,
    OnMtuChangedCallback,
    OnServicesDiscoveredCallback,
    PythonBluetoothGattCallback,
)
from bleak.backends.android.dispatcher import dispatch_func
from bleak.backends.android.permissions import check_for_permissions
from bleak.backends.android.utils import bitwise_or, context
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient, NotifyCallback
from bleak.backends.descriptor import BleakGATTDescriptor, normalize_uuid_16
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection
from bleak.exc import (
    BleakBluetoothNotAvailableError,
    BleakBluetoothNotAvailableReason,
    BleakError,
)

logger = logging.getLogger(__name__)

CCCD_DESCRIPTOR_UUID = normalize_uuid_16(0x2902)


@dataclasses.dataclass
class ConnectObjects:
    adapter: BluetoothAdapter
    device: BluetoothDevice
    gatt: BluetoothGatt
    callbacks: PythonBluetoothGattCallback
    subscriptions: dict[int, NotifyCallback]


class BleakClientAndroid(BaseBleakClient):
    """Android Bleak Client using Chaquopy/BeeWare.

    Args:
        address_or_ble_device:
            The Bluetooth address of the BLE peripheral to connect to or the
            :class:`BLEDevice` object representing it.
        services:
            Optional set of services UUIDs to filter.
    """

    def __init__(
        self,
        address_or_ble_device: Union[BLEDevice, str],
        services: Optional[set[uuid.UUID]],
        **kwargs: Any,
    ):
        super(BleakClientAndroid, self).__init__(address_or_ble_device, **kwargs)
        self._requested_services = (
            {UUID.fromString(str(u)) for u in services} if services else None
        )

        self._loop = asyncio.get_running_loop()
        self._mtu: int = 23
        self._conn_objs: Optional[ConnectObjects] = None

    # Connectivity methods

    @override
    async def connect(self, pair: bool, **kwargs: Any) -> None:
        """Connect to the specified GATT server."""
        if pair:
            logger.warning("Pairing during connect is not implemented on Android")

        timeout = kwargs.get("timeout", self._timeout)

        await check_for_permissions(self._loop)

        adapter = BluetoothAdapter.getDefaultAdapter()
        if adapter is None:
            raise BleakBluetoothNotAvailableError(
                "Bluetooth is not available",
                BleakBluetoothNotAvailableReason.NO_BLUETOOTH,
            )
        if adapter.getState() != BluetoothAdapter.STATE_ON:
            raise BleakBluetoothNotAvailableError(
                "Bluetooth is not turned on",
                BleakBluetoothNotAvailableReason.POWERED_OFF,
            )

        device = adapter.getRemoteDevice(self.address)
        callbacks = PythonBluetoothGattCallback(self, self._loop)
        subscriptions: dict[int, NotifyCallback] = {}

        logger.debug(f"Connecting to BLE device @ {self.address}")

        gatt, conn_future = callbacks.dispatcher.dispatch(
            dispatch_func=dispatch_func(
                device.connectGatt,
                context,
                False,
                callbacks.java,
                BluetoothDevice.TRANSPORT_LE,
            ),
            callback_api=OnConnectionStateChangeCallback(),
            dispatch_result_indicates_status=False,
        )
        try:
            conn_result = await asyncio.wait_for(conn_future, timeout=timeout)
            if conn_result.new_state != BluetoothProfile.STATE_CONNECTED:
                raise BleakError(
                    f"Unexpected connection state: {conn_result.new_state}"
                )
            logger.debug(f"{OnConnectionStateChangeCallback()} succeeded")
        except BaseException:
            # If connecting is canceled, times out, or fails, we need to disconnect to clean up the gatt connection.
            gatt.disconnect()
            gatt.close()
            raise

        self._conn_objs = ConnectObjects(
            adapter=adapter,
            device=device,
            gatt=gatt,
            callbacks=callbacks,
            subscriptions=subscriptions,
        )

        try:
            logger.debug("Connection successful.")

            # unlike other backends, Android doesn't automatically negotiate
            # the MTU, so we request the largest size possible like BlueZ
            logger.debug("requesting mtu...")
            result = await callbacks.dispatcher.perform_and_wait(
                dispatch_func=dispatch_func(gatt.requestMtu, 517),
                callback_api=OnMtuChangedCallback(),
            )
            self._mtu = result.mtu

            logger.debug("discovering services...")
            await callbacks.dispatcher.perform_and_wait(
                dispatch_func=dispatch_func(gatt.discoverServices),
                callback_api=OnServicesDiscoveredCallback(),
            )

            await self._get_services()
        except BaseException:
            # if connecting is canceled or one of the above fails, we need to
            # disconnect
            try:
                await self.disconnect()
            except Exception:
                pass
            raise

    @override
    async def disconnect(self) -> None:
        """Disconnect from the specified GATT server."""
        logger.debug("Disconnecting from BLE device...")
        if self._conn_objs is None:
            # No connection exists. Either one hasn't been created or
            # we have already called disconnect and closed the gatt
            # connection.
            logger.debug("already disconnected")
            return

        # Try to disconnect the actual device/peripheral
        try:
            # Skip if already disconnected (e.g. remote side closed the connection)
            conn_state = self._conn_objs.callbacks.dispatcher.states.get(
                OnConnectionStateChangeCallback()
            )
            already_disconnected = (
                conn_state is not None
                and isinstance(
                    conn_state.callback_result, OnConnectionStateChangeResult
                )
                and conn_state.callback_result.new_state
                == BluetoothProfile.STATE_DISCONNECTED
            )
            if not already_disconnected:
                _, future = self._conn_objs.callbacks.dispatcher.dispatch(
                    dispatch_func=dispatch_func(self._conn_objs.gatt.disconnect),
                    callback_api=OnConnectionStateChangeCallback(),
                    dispatch_result_indicates_status=False,  # gatt.disconnect() returns void
                )
                await future
            self._conn_objs.gatt.close()
        except Exception as e:
            logger.error(f"Attempt to disconnect device failed: {e}")

        self._conn_objs = None

        # Reset all stored services.
        self.services = None

    @override
    async def pair(self, *args: Any, **kwarg: Any) -> None:
        """Pair with the peripheral."""
        if self._conn_objs is None:
            raise BleakError("Not connected")

        bonded_future = self._loop.create_future()

        def handle_bond_state_changed(context: Context, intent: Intent):
            device = cast(
                BluetoothDevice | None,
                intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE),
            )
            assert device is not None
            if device.getAddress() != self.address:
                # Not the device we are interested in.
                return

            bond_state = intent.getIntExtra(BluetoothDevice.EXTRA_BOND_STATE, -1)
            if bond_state == BluetoothDevice.BOND_NONE:
                logger.debug("Device bonding failed.")
                self._loop.call_soon_threadsafe(
                    bonded_future.set_exception,
                    BleakError(
                        f"Device with address {self.address} could not be paired with."
                    ),
                )
            elif bond_state == BluetoothDevice.BOND_BONDED:
                logger.debug("Device successfully bonded.")
                self._loop.call_soon_threadsafe(bonded_future.set_result, True)
            elif bond_state == BluetoothDevice.BOND_BONDING:
                logger.debug("Device is bonding...")
            else:
                logger.debug(f"Unexpected bond state received {bond_state}.")
                self._loop.call_soon_threadsafe(
                    bonded_future.set_exception,
                    BleakError(f"Unexpected bond state {bond_state}"),
                )

        receiver = BroadcastReceiver(
            handle_bond_state_changed,
            actions=[BluetoothDevice.ACTION_BOND_STATE_CHANGED],
        )
        receiver.start()
        try:
            # See if it is already paired.
            bond_state = self._conn_objs.device.getBondState()
            if bond_state == BluetoothDevice.BOND_BONDED:
                return
            elif bond_state == BluetoothDevice.BOND_NONE:
                logger.debug(f"Pairing to BLE device @ {self.address}")
                if not self._conn_objs.device.createBond():
                    raise BleakError(
                        f"Could not initiate bonding with device @ {self.address}"
                    )
            await bonded_future
        finally:
            receiver.stop()

    @override
    async def unpair(self) -> None:
        """Unpair with the peripheral."""
        raise NotImplementedError("Unpairing is not implemented on Android")

    @property
    @override
    def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        if self._conn_objs is None:
            return False

        callback_state = self._conn_objs.callbacks.dispatcher.states.get(
            OnConnectionStateChangeCallback()
        )
        if callback_state is None:
            return False

        callback_result = callback_state.callback_result
        assert isinstance(callback_result, OnConnectionStateChangeResult)

        if callback_result.new_state != BluetoothProfile.STATE_CONNECTED:
            return False

        return True

    @property
    @override
    def name(self) -> str:
        if self._conn_objs is None:
            raise BleakError("Not connected")
        return self._conn_objs.device.getName() or ""

    @property
    @override
    def mtu_size(self) -> int:
        return self._mtu

    # GATT services methods

    async def _get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self.services is not None:
            return self.services

        if self._conn_objs is None:
            raise BleakError("Not connected")

        services = BleakGATTServiceCollection()

        logger.debug("Get Services...")
        for java_service in self._conn_objs.gatt.getServices().toArray():
            assert isinstance(java_service, BluetoothGattService)
            if (
                self._requested_services is not None
                and java_service.getUuid() not in self._requested_services
            ):
                continue

            service = BleakGATTService(
                java_service,
                java_service.getInstanceId(),
                str(java_service.getUuid()),
            )
            services.add_service(service)

            for java_characteristic in java_service.getCharacteristics().toArray():
                assert isinstance(java_characteristic, BluetoothGattCharacteristic)
                characteristic = BleakGATTCharacteristic(
                    java_characteristic,
                    java_characteristic.getInstanceId(),
                    str(java_characteristic.getUuid()),
                    list(gatt_char_props_to_strs(java_characteristic.getProperties())),
                    lambda: self._mtu - 3,
                    service,
                )
                services.add_characteristic(characteristic)

                for descriptor_index, java_descriptor in enumerate(
                    java_characteristic.getDescriptors().toArray()
                ):
                    assert isinstance(java_descriptor, BluetoothGattDescriptor)
                    descriptor = BleakGATTDescriptor(
                        java_descriptor,
                        characteristic.handle + 1 + descriptor_index,
                        str(java_descriptor.getUuid()),
                        characteristic,
                    )
                    services.add_descriptor(descriptor)

        self.services = services
        return self.services

    # IO methods

    @override
    async def read_gatt_char(
        self,
        characteristic: BleakGATTCharacteristic,
        *,
        use_cached: bool = False,
        **kwargs: Any,
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            characteristic (BleakGATTCharacteristic): The characteristic to read from.

        Returns:
            (bytearray) The read data.

        """
        if self._conn_objs is None:
            raise BleakError("Not connected")
        assert isinstance(characteristic.obj, BluetoothGattCharacteristic)

        if use_cached:
            value = bytearray(characteristic.obj.getValue())
            logger.debug(
                f"Read cached characteristic {characteristic.uuid} | {characteristic.handle}: {value}"
            )
            return value

        callback_result = await self._conn_objs.callbacks.dispatcher.perform_and_wait(
            dispatch_func=dispatch_func(
                self._conn_objs.gatt.readCharacteristic, characteristic.obj
            ),
            callback_api=OnCharacteristicReadCallback(characteristic.handle),
        )
        value = bytearray(callback_result.value)
        logger.debug(
            f"Read characteristic {characteristic.uuid} | {characteristic.handle}: {value}"
        )
        return value

    @override
    async def read_gatt_descriptor(
        self,
        descriptor: BleakGATTDescriptor,
        *,
        use_cached: bool = False,
        **kwargs: Any,
    ) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            descriptor: The descriptor to read from.
            use_cached: Whether to use cached value.

        Returns:
            The read data.
        """
        if self._conn_objs is None:
            raise BleakError("Not connected")
        assert isinstance(descriptor.obj, BluetoothGattDescriptor)

        if use_cached:
            value = bytearray(descriptor.obj.getValue())
            logger.debug(
                f"Read cached descriptor {descriptor.uuid} | {descriptor.handle}: {value}"
            )
            return value

        callback_result = await self._conn_objs.callbacks.dispatcher.perform_and_wait(
            dispatch_func=dispatch_func(
                self._conn_objs.gatt.readDescriptor, descriptor.obj
            ),
            callback_api=OnDescriptorReadCallback(uuid=descriptor.uuid),
        )
        value = bytearray(callback_result.value)

        logger.debug(
            f"Read descriptor {descriptor.uuid} | {descriptor.handle}: {value}"
        )

        return value

    @override
    async def write_gatt_char(
        self, characteristic: BleakGATTCharacteristic, data: SizedBuffer, response: bool
    ) -> None:
        if self._conn_objs is None:
            raise BleakError("Not connected")
        assert isinstance(characteristic.obj, BluetoothGattCharacteristic)

        write_type = (
            BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
            if response
            else BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        )

        gatt = self._conn_objs.gatt
        payload = jarray(jbyte)(bytes(data))

        if Build.VERSION.SDK_INT >= 33:

            def _do_write_char():  # pragma: no cover  # (CI is running on API level below 33)
                # On API level 33 (Android 13) and above writeCharacteristic returns int (GATT_SUCCESS=0 on success).
                # Convert to bool so dispatch_result_indicates_status=True works correctly.
                return (
                    gatt.writeCharacteristic(characteristic.obj, payload, write_type)
                    == 0
                )

        else:

            def _do_write_char():
                # On API level 32 (Android 12) and below writeCharacteristic returns boolean success.
                characteristic.obj.setWriteType(write_type)
                characteristic.obj.setValue(payload)
                return gatt.writeCharacteristic(characteristic.obj)

        await self._conn_objs.callbacks.dispatcher.perform_and_wait(
            dispatch_func=_do_write_char,
            callback_api=OnCharacteristicWriteCallback(
                handle=characteristic.handle,
            ),
        )

        logger.debug(
            f"Write Characteristic {characteristic.uuid} | {characteristic.handle}: {data}"
        )

    @override
    async def write_gatt_descriptor(
        self, descriptor: BleakGATTDescriptor, data: SizedBuffer
    ) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            data (bytes or bytearray): The data to send.

        """
        if self._conn_objs is None:
            raise BleakError("Not connected")
        assert self.services
        assert isinstance(descriptor.obj, BluetoothGattDescriptor)

        gatt = self._conn_objs.gatt
        payload = jarray(jbyte)(bytes(data))

        if Build.VERSION.SDK_INT >= 33:

            def _do_write_desc():  # pragma: no cover  # (CI is running on API level below 33)
                # On API level 33 (Android 13) and above writeDescriptor returns int (GATT_SUCCESS=0 on success).
                # Convert to bool so dispatch_result_indicates_status=True works correctly.
                return gatt.writeDescriptor(descriptor.obj, payload) == 0

        else:

            def _do_write_desc():
                # On API level 32 (Android 12) and below writeDescriptor returns boolean success.
                descriptor.obj.setValue(payload)
                return gatt.writeDescriptor(descriptor.obj)

        await self._conn_objs.callbacks.dispatcher.perform_and_wait(
            dispatch_func=_do_write_desc,
            callback_api=OnDescriptorWriteCallback(uuid=descriptor.uuid),
        )

        logger.debug(
            f"Write Descriptor {descriptor.uuid} | {descriptor.handle}: {data}"
        )

    @override
    async def start_notify(
        self,
        characteristic: BleakGATTCharacteristic,
        callback: NotifyCallback,
        **kwargs: Any,
    ) -> None:
        """
        Activate notifications/indications on a characteristic.
        """
        if self._conn_objs is None:
            raise BleakError("Not connected")

        assert isinstance(characteristic.obj, BluetoothGattCharacteristic)

        cccd = characteristic.get_descriptor(CCCD_DESCRIPTOR_UUID)
        if cccd is None:
            raise BleakError(
                f"Characteristic {characteristic.uuid} does not have a CCCD descriptor"
            )

        props = characteristic.obj.getProperties()
        if (
            props & BluetoothGattCharacteristic.PROPERTY_INDICATE
            and props & BluetoothGattCharacteristic.PROPERTY_NOTIFY
        ):
            cccd_value = bitwise_or(
                bytes(BluetoothGattDescriptor.ENABLE_INDICATION_VALUE),
                bytes(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE),
            )
        elif props & BluetoothGattCharacteristic.PROPERTY_INDICATE:
            cccd_value = bytes(BluetoothGattDescriptor.ENABLE_INDICATION_VALUE)
        elif props & BluetoothGattCharacteristic.PROPERTY_NOTIFY:
            cccd_value = bytes(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE)
        else:
            raise BleakError(
                f"Characteristic {characteristic.uuid} does not support Notify or Indicate"
            )

        self._conn_objs.subscriptions[characteristic.handle] = callback
        try:
            if not self._conn_objs.gatt.setCharacteristicNotification(
                characteristic.obj, True
            ):
                raise BleakError(
                    f"Failed to enable notification for characteristic {characteristic.uuid}"
                )

            await self.write_gatt_descriptor(
                cccd,
                cccd_value,
            )
        except Exception:
            self._conn_objs.subscriptions.pop(characteristic.handle, None)
            raise

    @override
    async def stop_notify(self, characteristic: BleakGATTCharacteristic) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            characteristic (BleakGATTCharacteristic): The characteristic to deactivate
                notification/indication on,.

        """
        if self._conn_objs is None:
            raise BleakError("Not connected")

        cccd = characteristic.get_descriptor(CCCD_DESCRIPTOR_UUID)
        if cccd is None:
            raise BleakError(
                f"Characteristic {characteristic.uuid} does not have a CCCD descriptor"
            )

        await self.write_gatt_descriptor(
            cccd,
            bytes(BluetoothGattDescriptor.DISABLE_NOTIFICATION_VALUE),
        )

        if not self._conn_objs.gatt.setCharacteristicNotification(
            characteristic.obj, False
        ):
            raise BleakError(
                f"Failed to disable notification for characteristic {characteristic.uuid}"
            )

        self._conn_objs.subscriptions.pop(characteristic.handle, None)
