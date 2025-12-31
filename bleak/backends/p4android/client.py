"""
BLE Client for python-for-android
"""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import asyncio
import logging
import uuid
import warnings
from typing import Any, Optional, Union

from android.broadcast import BroadcastReceiver
from jnius import java_method

from bleak._compat import override
from bleak.assigned_numbers import gatt_char_props_to_strs
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient, NotifyCallback
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.device import BLEDevice
from bleak.backends.p4android import defs, utils
from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection
from bleak.exc import BleakError

logger = logging.getLogger(__name__)


class BleakClientP4Android(BaseBleakClient):
    """A python-for-android Bleak Client

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
        **kwargs,
    ):
        super().__init__(address_or_ble_device, **kwargs)
        self._requested_services = (
            set(map(defs.UUID.fromString, services)) if services else None
        )
        # kwarg "device" is for backwards compatibility
        self.__adapter = kwargs.get("adapter", kwargs.get("device", None))
        self.__gatt = None
        self.__mtu = 23

        self.__callbacks = None

    # Connectivity methods

    @override
    async def connect(self, pair: bool, **kwargs) -> None:
        """Connect to the specified GATT server."""
        if pair:
            logger.warning("Pairing during connect is not implemented on Android")

        loop = asyncio.get_running_loop()

        self.__adapter = defs.BluetoothAdapter.getDefaultAdapter()
        if self.__adapter is None:
            raise BleakError("Bluetooth is not supported on this hardware platform")
        if self.__adapter.getState() != defs.BluetoothAdapter.STATE_ON:
            raise BleakError("Bluetooth is not turned on")

        self.__device = self.__adapter.getRemoteDevice(self.address)

        self.__callbacks = _PythonBluetoothGattCallback(self, loop)

        self._subscriptions = {}

        logger.debug(f"Connecting to BLE device @ {self.address}")

        (self.__gatt,) = await self.__callbacks.perform_and_wait(
            dispatchApi=self.__device.connectGatt,
            dispatchParams=(
                defs.context,
                False,
                self.__callbacks.java,
                defs.BluetoothDevice.TRANSPORT_LE,
            ),
            resultApi="onConnectionStateChange",
            resultExpected=(defs.BluetoothProfile.STATE_CONNECTED,),
            return_indicates_status=False,
        )

        try:
            logger.debug("Connection successful.")

            # unlike other backends, Android doesn't automatically negotiate
            # the MTU, so we request the largest size possible like BlueZ
            logger.debug("requesting mtu...")
            (self.__mtu,) = await self.__callbacks.perform_and_wait(
                dispatchApi=self.__gatt.requestMtu,
                dispatchParams=(517,),
                resultApi="onMtuChanged",
            )

            logger.debug("discovering services...")
            await self.__callbacks.perform_and_wait(
                dispatchApi=self.__gatt.discoverServices,
                dispatchParams=(),
                resultApi="onServicesDiscovered",
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
        if self.__gatt is None:
            # No connection exists. Either one hasn't been created or
            # we have already called disconnect and closed the gatt
            # connection.
            logger.debug("already disconnected")
            return

        # Try to disconnect the actual device/peripheral
        try:
            await self.__callbacks.perform_and_wait(
                dispatchApi=self.__gatt.disconnect,
                dispatchParams=(),
                resultApi="onConnectionStateChange",
                resultExpected=(defs.BluetoothProfile.STATE_DISCONNECTED,),
                unless_already=True,
                return_indicates_status=False,
            )
            self.__gatt.close()
        except Exception as e:
            logger.error(f"Attempt to disconnect device failed: {e}")

        self.__gatt = None
        self.__callbacks = None

        # Reset all stored services.
        self.services = None

    @override
    async def pair(self, *args, **kwargs) -> None:
        """Pair with the peripheral.

        You can use ConnectDevice method if you already know the MAC address of the device.
        Else you need to StartDiscovery, Trust, Pair and Connect in sequence.
        """
        loop = asyncio.get_running_loop()

        bondedFuture = loop.create_future()

        def handleBondStateChanged(context, intent):
            bond_state = intent.getIntExtra(defs.BluetoothDevice.EXTRA_BOND_STATE, -1)
            if bond_state == -1:
                loop.call_soon_threadsafe(
                    bondedFuture.set_exception,
                    BleakError(f"Unexpected bond state {bond_state}"),
                )
            elif bond_state == defs.BluetoothDevice.BOND_NONE:
                loop.call_soon_threadsafe(
                    bondedFuture.set_exception,
                    BleakError(
                        f"Device with address {self.address} could not be paired with."
                    ),
                )
            elif bond_state == defs.BluetoothDevice.BOND_BONDED:
                loop.call_soon_threadsafe(bondedFuture.set_result, True)

        receiver = BroadcastReceiver(
            handleBondStateChanged,
            actions=[defs.BluetoothDevice.ACTION_BOND_STATE_CHANGED],
        )
        receiver.start()
        try:
            # See if it is already paired.
            bond_state = self.__device.getBondState()
            if bond_state == defs.BluetoothDevice.BOND_BONDED:
                return
            elif bond_state == defs.BluetoothDevice.BOND_NONE:
                logger.debug(f"Pairing to BLE device @ {self.address}")
                if not self.__device.createBond():
                    raise BleakError(
                        f"Could not initiate bonding with device @ {self.address}"
                    )
            await bondedFuture
        finally:
            await receiver.stop()

    @override
    async def unpair(self) -> None:
        """Unpair with the peripheral."""
        warnings.warn(
            "Unpairing is seemingly unavailable in the Android API at the moment."
        )

    @property
    @override
    def is_connected(self) -> bool:
        """Check connection status between this client and the server.

        Returns:
            Boolean representing connection status.

        """
        return (
            self.__callbacks is not None
            and self.__callbacks.states["onConnectionStateChange"][1]
            == defs.BluetoothProfile.STATE_CONNECTED
        )

    @property
    @override
    def mtu_size(self) -> int:
        return self.__mtu

    # GATT services methods

    async def _get_services(self) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        Returns:
           A :py:class:`bleak.backends.service.BleakGATTServiceCollection` with this device's services tree.

        """
        if self.services is not None:
            return self.services

        services = BleakGATTServiceCollection()

        logger.debug("Get Services...")
        for java_service in self.__gatt.getServices():
            if (
                self._requested_services is not None
                and java_service.getUuid() not in self._requested_services
            ):
                continue

            service = BleakGATTService(
                java_service,
                java_service.getInstanceId(),
                java_service.getUuid().toString(),
            )
            services.add_service(service)

            for java_characteristic in java_service.getCharacteristics():

                characteristic = BleakGATTCharacteristic(
                    java_characteristic,
                    java_characteristic.getInstanceId(),
                    java_characteristic.getUuid().toString(),
                    gatt_char_props_to_strs(java_characteristic.getProperties()),
                    lambda: self.__mtu - 3,
                    service,
                )
                services.add_characteristic(characteristic)

                for descriptor_index, java_descriptor in enumerate(
                    java_characteristic.getDescriptors()
                ):

                    descriptor = BleakGATTDescriptor(
                        java_descriptor,
                        characteristic.handle + 1 + descriptor_index,
                        java_descriptor.getUuid().toString(),
                        characteristic,
                    )
                    services.add_descriptor(descriptor)

        self.services = services
        return self.services

    # IO methods

    @override
    async def read_gatt_char(
        self, characteristic: BleakGATTCharacteristic, **kwargs: Any
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        Args:
            characteristic (BleakGATTCharacteristic): The characteristic to read from.

        Returns:
            (bytearray) The read data.

        """

        (value,) = await self.__callbacks.perform_and_wait(
            dispatchApi=self.__gatt.readCharacteristic,
            dispatchParams=(characteristic.obj,),
            resultApi=("onCharacteristicRead", characteristic.handle),
        )
        value = bytearray(value)
        logger.debug(
            f"Read Characteristic {characteristic.uuid} | {characteristic.handle}: {value}"
        )
        return value

    @override
    async def read_gatt_descriptor(
        self, descriptor: BleakGATTDescriptor, **kwargs: Any
    ) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        Args:
            descriptor: The descriptor to read from.

        Returns:
            The read data.
        """
        (value,) = await self.__callbacks.perform_and_wait(
            dispatchApi=self.__gatt.readDescriptor,
            dispatchParams=(descriptor.obj,),
            resultApi=("onDescriptorRead", descriptor.uuid),
        )
        value = bytearray(value)

        logger.debug(
            f"Read Descriptor {descriptor.uuid} | {descriptor.handle}: {value}"
        )

        return value

    @override
    async def write_gatt_char(
        self, characteristic: BleakGATTCharacteristic, data: bytearray, response: bool
    ) -> None:
        if response:
            characteristic.obj.setWriteType(
                defs.BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
            )
        else:
            characteristic.obj.setWriteType(
                defs.BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
            )

        characteristic.obj.setValue(data)

        await self.__callbacks.perform_and_wait(
            dispatchApi=self.__gatt.writeCharacteristic,
            dispatchParams=(characteristic.obj,),
            resultApi=("onCharacteristicWrite", characteristic.handle),
        )

        logger.debug(
            f"Write Characteristic {characteristic.uuid} | {characteristic.handle}: {data}"
        )

    @override
    async def write_gatt_descriptor(
        self,
        desc_specifier: Union[BleakGATTDescriptor, str, uuid.UUID],
        data: bytearray,
    ) -> None:
        """Perform a write operation on the specified GATT descriptor.

        Args:
            desc_specifier (BleakGATTDescriptor, str or UUID): The descriptor to write
                to, specified by either UUID or directly by the
                BleakGATTDescriptor object representing it.
            data (bytes or bytearray): The data to send.

        """
        if not isinstance(desc_specifier, BleakGATTDescriptor):
            descriptor = self.services.get_descriptor(desc_specifier)
        else:
            descriptor = desc_specifier

        if not descriptor:
            raise BleakError(f"Descriptor {desc_specifier} was not found!")

        descriptor.obj.setValue(data)

        await self.__callbacks.perform_and_wait(
            dispatchApi=self.__gatt.writeDescriptor,
            dispatchParams=(descriptor.obj,),
            resultApi=("onDescriptorWrite", descriptor.uuid),
        )

        logger.debug(
            f"Write Descriptor {descriptor.uuid} | {descriptor.handle}: {data}"
        )

    @override
    async def start_notify(
        self,
        characteristic: BleakGATTCharacteristic,
        callback: NotifyCallback,
        **kwargs,
    ) -> None:
        """
        Activate notifications/indications on a characteristic.
        """
        self._subscriptions[characteristic.handle] = callback

        assert self.__gatt is not None

        if not self.__gatt.setCharacteristicNotification(characteristic.obj, True):
            raise BleakError(
                f"Failed to enable notification for characteristic {characteristic.uuid}"
            )

        await self.write_gatt_descriptor(
            characteristic.notification_descriptor,
            defs.BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE,
        )

    @override
    async def stop_notify(self, characteristic: BleakGATTCharacteristic) -> None:
        """Deactivate notification/indication on a specified characteristic.

        Args:
            characteristic (BleakGATTCharacteristic): The characteristic to deactivate
                notification/indication on,.

        """
        await self.write_gatt_descriptor(
            characteristic.notification_descriptor,
            defs.BluetoothGattDescriptor.DISABLE_NOTIFICATION_VALUE,
        )

        if not self.__gatt.setCharacteristicNotification(characteristic.obj, False):
            raise BleakError(
                f"Failed to disable notification for characteristic {characteristic.uuid}"
            )
        del self._subscriptions[characteristic.handle]


class _PythonBluetoothGattCallback(utils.AsyncJavaCallbacks):
    __javainterfaces__ = [
        "com.github.hbldh.bleak.PythonBluetoothGattCallback$Interface"
    ]

    def __init__(self, client, loop):
        super().__init__(loop)
        self._client = client
        self.java = defs.PythonBluetoothGattCallback(self)

    def result_state(self, status, resultApi, *data):
        if status == defs.BluetoothGatt.GATT_SUCCESS:
            failure_str = None
        else:
            failure_str = defs.GATT_STATUS_STRINGS.get(status, status)
        self._loop.call_soon_threadsafe(
            self._result_state_unthreadsafe, failure_str, resultApi, data
        )

    @java_method("(II)V")
    def onConnectionStateChange(self, status, new_state):
        try:
            self.result_state(status, "onConnectionStateChange", new_state)
        except BleakError:
            pass
        if (
            new_state == defs.BluetoothProfile.STATE_DISCONNECTED
            and self._client._disconnected_callback is not None
        ):
            self._client._disconnected_callback()

    @java_method("(II)V")
    def onMtuChanged(self, mtu, status):
        self.result_state(status, "onMtuChanged", mtu)

    @java_method("(I)V")
    def onServicesDiscovered(self, status):
        self.result_state(status, "onServicesDiscovered")

    @java_method("(I[B)V")
    def onCharacteristicChanged(self, handle, value):
        self._loop.call_soon_threadsafe(
            self._client._subscriptions[handle], bytearray(value.tolist())
        )

    @java_method("(II[B)V")
    def onCharacteristicRead(self, handle, status, value):
        self.result_state(
            status, ("onCharacteristicRead", handle), bytes(value.tolist())
        )

    @java_method("(II)V")
    def onCharacteristicWrite(self, handle, status):
        self.result_state(status, ("onCharacteristicWrite", handle))

    @java_method("(Ljava/lang/String;I[B)V")
    def onDescriptorRead(self, uuid, status, value):
        self.result_state(status, ("onDescriptorRead", uuid), bytes(value.tolist()))

    @java_method("(Ljava/lang/String;I)V")
    def onDescriptorWrite(self, uuid, status):
        self.result_state(status, ("onDescriptorWrite", uuid))
