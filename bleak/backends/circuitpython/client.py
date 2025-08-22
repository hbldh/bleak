import logging
import asyncio
from typing import Optional, Any
from uuid import UUID

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
        self._timeout = 10

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

        if not self._advertisement.connectable:
            raise BleakError("Device is not connectable")

        timeout = kwargs.get("timeout", self._timeout)

        if self._advertisement is None:
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

        logger.debug("Connecting to BLE device @ {}".format(self.address))

        self._connection = await asyncio.create_task(self._connect_task())
        if not self.is_connected:
            raise BleakError("Device is not connected")

        logger.debug("Connected to BLE device @ {}".format(self.address))

        logger.debug("Retrieving services from BLE device @ {}".format(self.address))

        # TODO: отримати сервіси, обгорнувши синхронний виклик у asyncio.to_thread
        discovered_services_tuple = await asyncio.create_task(self._discover_services_task())
        print(discovered_services_tuple)
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

        await asyncio.create_task(self._disconnect_task())
        self._connection = None

        logger.debug("Device disconnected @ {}".format(self.address))

    async def _connect_task(self):
        return self._radio.connect(self._advertisement.address)

    async def _disconnect_task(self):
        """Helper to run the blocking disconnect call."""
        if self.is_connected:
            self._connection.disconnect()

    async def _discover_services_task(self):
        if hasattr(self._connection, "_bleio_connection"):
            bleio_conn = self._connection._bleio_connection
            if hasattr(bleio_conn, "discover_remote_services"):
                await asyncio.sleep(1.0)
                try:
                    await asyncio.sleep(1)
                    return bleio_conn.discover_remote_services()
                except Exception as e:
                    raise BleakError(f"Failed to discover remote services: {e}")
        raise BleakError("Discover remote services not available")

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
