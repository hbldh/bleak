import logging
from typing import Optional, Any
from typing_extensions import override

from _bleio import set_adapter
from adafruit_ble import BLERadio, Advertisement, BLEConnection

from bleak import BleakScanner
from bleak.backends.circuitpython.scanner import BleakScannerCircuitPython
from bleak.backends.client import BaseBleakClient
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError, BleakDeviceNotFoundError

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class BleakClientCircuitPython(BaseBleakClient):
    def __init__(
        self,
        address_or_ble_device: BLEDevice,
        services=None,
        **kwargs,
    ):
        super().__init__(address_or_ble_device, **kwargs)
        _adapter = kwargs.get("adapter")
        if _adapter is not None:
            set_adapter(_adapter)

        self._radio: Optional[BLERadio] = None
        self._advertisement: Optional[Advertisement] = None

        if isinstance(address_or_ble_device, BLEDevice):
            self._radio, self._advertisement = address_or_ble_device.details

        self._connection: Optional[BLEConnection] = None
        # self._services = None
        # self._is_connected = False
        # self._mtu = 23

    @override
    async def connect(self, pair, dangerous_use_bleak_cache=False, **kwargs):
        logger.debug("Attempting to connect BLE device @ {}".format(self.address))

        if self.is_connected:
            raise BleakError("Client is already connected")

        if not self._advertisement.connectable:
            raise BleakError("Device is not connectable")

        if pair:
            raise NotImplementedError("Not yet implemented")

        timeout = kwargs.get("timeout", self._timeout)

        if self._advertisement is None:
            logger.debug("Attempting to find BLE device @ {}".format(self.address))

            device = await BleakScanner.find_device_by_address(
                self.address, timeout=timeout, backend=BleakScannerCircuitPython
            )
            if device:
                self._radio, self._advertisement = device.details
            else:
                raise BleakDeviceNotFoundError(
                    self.address, f"Device @ {self.address} was not found"
                )

        if self._radio is None:
            self._radio = BLERadio()

        # TODO: disconnect_callback ?

        logger.debug("Connecting to BLE device @ {}".format(self.address))

        # TODO: wrap async
        self._connection = self._radio.connect(self._advertisement.address, timeout=timeout)
        logger.debug("Connected to BLE device @ {}".format(self.address))

        logger.debug("Retrieving services from BLE device @ {}".format(self.address))

        # TODO: get services

        logger.debug("Services retrieved from BLE device @ {}".format(self.address))


    async def disconnect(self) -> None:
        """Disconnect from the peripheral device"""
        logger.debug("Disconnecting from BLE device @ {}".format(self.address))
        if (
            self._radio is None
            or self._advertisement is None
            or not self.is_connected
        ):
            logger.debug("Device is not connected @ {}".format(self.address))
            return

        # TODO: wrap async
        self._connection.disconnect()
        logger.debug("Device disconnected @ {}".format(self.address))

    @property
    @override
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.connected

    @property
    @override
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection"""
        # TODO: implement
        raise NotImplementedError()

    @override
    async def pair(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError()

    @override
    async def unpair(self) -> None:
        raise NotImplementedError()

    @override
    async def read_gatt_char(self, characteristic, **kwargs):
        ...

    @override
    async def read_gatt_descriptor(self, descriptor: BleakGATTDescriptor, **kwargs):
        ...

    @override
    async def write_gatt_char(self, characteristic, data, response):
        ...

    @override
    async def write_gatt_descriptor(self, descriptor, data):
        ...

    @override
    async def start_notify(
        self,
        characteristic,
        callback,
        **kwargs,
    ):
        ...

    @override
    async def stop_notify(self, characteristic):
        ...

    async def get_rssi(self) -> int:
        assert self._advertisement
        return self._advertisement.rssi
