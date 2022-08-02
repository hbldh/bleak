"""
BLE Client for CoreBluetooth on macOS

Created on 2019-06-26 by kevincar <kevincarrolldavis@gmail.com>
"""
import asyncio
import inspect
import logging
import uuid
from typing import Callable, Optional, Union

from Foundation import NSArray, NSData
from CoreBluetooth import (
    CBCharacteristicWriteWithResponse,
    CBCharacteristicWriteWithoutResponse,
    CBPeripheral,
    CBPeripheralStateConnected,
)

from bleak.backends.client import BaseBleakClient
from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
from bleak.backends.corebluetooth.characteristic import (
    BleakGATTCharacteristicCoreBluetooth,
)
from bleak.backends.corebluetooth.descriptor import BleakGATTDescriptorCoreBluetooth
from bleak.backends.corebluetooth.PeripheralDelegate import PeripheralDelegate
from bleak.backends.corebluetooth.scanner import BleakScannerCoreBluetooth
from bleak.backends.corebluetooth.service import BleakGATTServiceCoreBluetooth
from bleak.backends.corebluetooth.utils import cb_uuid_to_str
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTServiceCollection
from bleak.backends.characteristic import BleakGATTCharacteristic

from bleak.exc import BleakError

logger = logging.getLogger(__name__)


class BleakClientCoreBluetooth(BaseBleakClient):
    """API for connecting to a BLE server and communicating with it, CoreBluetooth implementation.

    Documentation:
    https://developer.apple.com/documentation/corebluetooth/cbcentralmanager

    CoreBluetooth doesn't explicitly use Bluetooth addresses to identify peripheral
    devices because private devices may obscure their Bluetooth addresses. To cope
    with this, CoreBluetooth utilizes UUIDs for each peripheral. Bleak uses
    this for the BLEDevice address on macOS.

    A BleakClient can be used as an asynchronous context manager in which case it automatically
    connects and disconnects.

    :param address_or_ble_device: The server to connect to, specified as BLEDevice or backend-dependent Bluetooth address.
    :type address_or_ble_device: Union[BLEDevice, str]
    :param timeout: Timeout for required ``discover`` call. Defaults to 10.0.
    :type timeout: float
    :param disconnected_callback: Callback that will be scheduled in the
            event loop when the client is disconnected.
    :type disconnected_callback: Callable[[BleakClient], None]
    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super(BleakClientCoreBluetooth, self).__init__(address_or_ble_device, **kwargs)

        self._peripheral: Optional[CBPeripheral] = None
        self._delegate: Optional[PeripheralDelegate] = None
        self._central_manager_delegate: Optional[CentralManagerDelegate] = None

        if isinstance(address_or_ble_device, BLEDevice):
            self._peripheral = address_or_ble_device.details
            self._central_manager_delegate = address_or_ble_device.metadata["delegate"]

        self._services: Optional[NSArray] = None

    def __str__(self):
        return "BleakClientCoreBluetooth ({})".format(self.address)

    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server, CoreBluetooth implementation.

        :param timeout: Timeout for required ``BleakScanner.find_device_by_address`` call. Defaults to 10.0.
        :type timeout: float
        :returns: true if succesful.
        """
        timeout = kwargs.get("timeout", self._timeout)
        if self._peripheral is None:
            device = await BleakScannerCoreBluetooth.find_device_by_address(
                self.address, timeout=timeout
            )

            if device:
                self._peripheral = device.details
                self._central_manager_delegate = device.metadata["delegate"]
            else:
                raise BleakError(
                    "Device with address {} was not found".format(self.address)
                )

        if self._delegate is None:
            self._delegate = PeripheralDelegate.alloc().initWithPeripheral_(
                self._peripheral
            )

        def disconnect_callback():
            self.services = BleakGATTServiceCollection()
            # Ensure that `get_services` retrieves services again, rather
            # than using the cached object
            self._services_resolved = False
            self._services = None

            # If there are any pending futures waiting for delegate callbacks, we
            # need to raise an exception since the callback will no longer be
            # called because the device is disconnected.
            for future in self._delegate.futures():
                try:
                    future.set_exception(BleakError("disconnected"))
                except asyncio.InvalidStateError:
                    # the future was already done
                    pass

            if self._disconnected_callback:
                self._disconnected_callback(self)

        manager = self._central_manager_delegate
        logger.debug("CentralManagerDelegate  at {}".format(manager))
        logger.debug("Connecting to BLE device @ {}".format(self.address))
        await manager.connect(self._peripheral, disconnect_callback, timeout=timeout)

        # Now get services
        await self.get_services()

        return True

    async def disconnect(self) -> bool:
        if (
            self._peripheral is None
            or self._peripheral.state() != CBPeripheralStateConnected
        ):
            return True

        await self._central_manager_delegate.disconnect(self._peripheral)

        return True

    @property
    def is_connected(self) -> bool:
        return self._DeprecatedIsConnectedReturn(
            False
            if self._peripheral is None
            else self._peripheral.state() == CBPeripheralStateConnected
        )

    @property
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection (CoreBluetooth specific)"""
        # Use type CBCharacteristicWriteWithoutResponse to get maximum write
        # value length based on the negotiated ATT MTU size. Add the ATT header
        # length (+3) to get the actual ATT MTU size.
        return (
            self._peripheral.maximumWriteValueLengthForType_(
                CBCharacteristicWriteWithoutResponse
            )
            + 3
        )

    async def pair(self, *args, **kwargs) -> bool:
        """Attempt to pair with a peripheral, CoreBluetooth implementation.

        .. note::

            This is not available on macOS since there is not explicit method to do a pairing, Instead the docs
            state that it "auto-pairs" when trying to read a characteristic that requires encryption, something
            Bleak cannot do apparently.

        Reference:

            - `Apple Docs <https://developer.apple.com/library/archive/documentation/NetworkingInternetWeb/Conceptual/CoreBluetooth_concepts/BestPracticesForSettingUpYourIOSDeviceAsAPeripheral/BestPracticesForSettingUpYourIOSDeviceAsAPeripheral.html#//apple_ref/doc/uid/TP40013257-CH5-SW1>`_
            - `Stack Overflow post #1 <https://stackoverflow.com/questions/25254932/can-you-pair-a-bluetooth-le-device-in-an-ios-app>`_
            - `Stack Overflow post #2 <https://stackoverflow.com/questions/47546690/ios-bluetooth-pairing-request-dialog-can-i-know-the-users-choice>`_

        Returns:
            Boolean regarding success of pairing.

        """
        raise NotImplementedError("Pairing is not available in Core Bluetooth.")

    async def unpair(self) -> bool:
        raise NotImplementedError("Pairing is not available in Core Bluetooth.")

    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        if self._services is not None:
            return self.services

        logger.debug("Retrieving services...")
        services = await self._delegate.discover_services()

        for service in services:
            serviceUUID = service.UUID().UUIDString()
            logger.debug(
                "Retrieving characteristics for service {}".format(serviceUUID)
            )
            characteristics = await self._delegate.discover_characteristics(service)

            self.services.add_service(BleakGATTServiceCoreBluetooth(service))

            for characteristic in characteristics:
                cUUID = characteristic.UUID().UUIDString()
                logger.debug(
                    "Retrieving descriptors for characteristic {}".format(cUUID)
                )
                descriptors = await self._delegate.discover_descriptors(characteristic)

                self.services.add_characteristic(
                    BleakGATTCharacteristicCoreBluetooth(characteristic)
                )
                for descriptor in descriptors:
                    self.services.add_descriptor(
                        BleakGATTDescriptorCoreBluetooth(
                            descriptor,
                            cb_uuid_to_str(characteristic.UUID()),
                            int(characteristic.handle()),
                        )
                    )
        logger.debug("Services resolved for %s", str(self))
        self._services_resolved = True
        self._services = services
        return self.services

    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        use_cached=False,
        **kwargs,
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic, CoreBluetooth implementation.

        The use_cached keyword argument is CoreBluetooth-specific.

        :param char_specifier: The characteristic to read from ((BleakGATTCharacteristic, handle or UUID))
        :param use_cached: ``False`` forces CoreBluetooth to read the value from the
                device again and not use its own cached value. Defaults to ``False``.


        :returns: The data read (bytearray without any conversion).

        """
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} was not found!".format(char_specifier))

        output = await self._delegate.read_characteristic(
            characteristic.obj, use_cached=use_cached
        )
        value = bytearray(output)
        logger.debug("Read Characteristic {0} : {1}".format(characteristic.uuid, value))
        return value

    async def read_gatt_descriptor(
        self, handle: int, use_cached=False, **kwargs
    ) -> bytearray:
        """Perform read operation on the specified GATT descriptor, CoreBluetooth implementation.

        The use_cached keyword argument is CoreBluetooth-specific.

        :param handle: The handle of the descriptor to read from.
        :param use_cached: ``False`` forces CoreBluetooth to read the value from the
                device again and not use its own cached value. Defaults to ``False``.
        :returns: (bytearray) The read data.

        """
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor {} was not found!".format(handle))

        output = await self._delegate.read_descriptor(
            descriptor.obj, use_cached=use_cached
        )
        if isinstance(
            output, str
        ):  # Sometimes a `pyobjc_unicode`or `__NSCFString` is returned and they can be used as regular Python strings.
            value = bytearray(output.encode("utf-8"))
        else:  # _NSInlineData
            value = bytearray(output)  # value.getBytes_length_(None, len(value))
        logger.debug("Read Descriptor {0} : {1}".format(handle, value))
        return value

    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        data: Union[bytes, bytearray, memoryview],
        response: bool = False,
    ) -> None:
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} was not found!".format(char_specifier))

        value = NSData.alloc().initWithBytes_length_(data, len(data))
        await self._delegate.write_characteristic(
            characteristic.obj,
            value,
            CBCharacteristicWriteWithResponse
            if response
            else CBCharacteristicWriteWithoutResponse,
        )
        logger.debug(f"Write Characteristic {characteristic.uuid} : {data}")

    async def write_gatt_descriptor(
        self, handle: int, data: Union[bytes, bytearray, memoryview]
    ) -> None:
        descriptor = self.services.get_descriptor(handle)
        if not descriptor:
            raise BleakError("Descriptor {} was not found!".format(handle))

        value = NSData.alloc().initWithBytes_length_(data, len(data))
        await self._delegate.write_descriptor(descriptor.obj, value)
        logger.debug("Write Descriptor {0} : {1}".format(handle, data))

    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs,
    ) -> None:
        if inspect.iscoroutinefunction(callback):

            def bleak_callback(s, d):
                asyncio.ensure_future(callback(s, d))

        else:
            bleak_callback = callback

        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {0} not found!".format(char_specifier))

        await self._delegate.start_notifications(characteristic.obj, bleak_callback)

    async def stop_notify(
        self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID]
    ) -> None:
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} not found!".format(char_specifier))

        await self._delegate.stop_notifications(characteristic.obj)

    async def get_rssi(self) -> int:
        """Get RSSI value in dBm of the connected Peripheral, CoreBluetooth-specific"""
        return int(await self._delegate.read_rssi())
