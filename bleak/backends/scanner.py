import abc
import asyncio
from typing import Callable, Dict, List, Optional, Tuple

from bleak.backends.device import BLEDevice


class AdvertisementData:
    """
    Wrapper around the advertisement data that each platform returns upon discovery
    """

    def __init__(self, address: str, **kwargs):
        """
        Required Args:
            address (str): The platform specific address of the device

        Keyword Args:
            local_name (str): The name of the ble device advertising
            rssi (int): Rssi value of the device
            manufacturer_data (dict): Manufacturer data from the device
            service_data (dict): Service data from the device
            service_uuids (list): UUIDs associated with the device
            platform_data (tuple): Tuple of platform specific advertisement data
        """
        # Platform specific address of the device
        self.address: str = address

        # The local name of the device
        self.local_name: Optional[str] = kwargs.get("local_name", None)

        # Integer RSSI value from the device
        self.rssi: int = kwargs.get("rssi", 0)

        # Dictionary of manufacturer data in bytes
        self.manufacturer_data: Dict[int, bytes] = kwargs.get("manufacturer_data", {})

        # Dictionary of service data
        self.service_data: Dict[str, bytes] = kwargs.get("service_data", {})

        # List of UUIDs
        self.service_uuids: List[str] = kwargs.get("service_uuids", [])

        # Tuple of platform specific data
        self.platform_data: Tuple = kwargs.get("platform_data", ())

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        kwargs = ""
        if self.local_name:
            kwargs += f", local_name={repr(self.local_name)}"
        if self.rssi:
            kwargs += f", rssi={repr(self.rssi)}"
        if self.manufacturer_data:
            kwargs += f", manufacturer_data={repr(self.manufacturer_data)}"
        if self.service_data:
            kwargs += f", service_data={repr(self.service_data)}"
        if self.service_uuids:
            kwargs += f", service_uuids={repr(self.service_uuids)}"
        if self.platform_data:
            kwargs += f", platform_data={repr(self.platform_data)}"
        return f"AdvertisementData({repr(self.address)}{kwargs})"


class BaseBleakScanner(abc.ABC):
    """Interface for Bleak Bluetooth LE Scanners"""

    def __init__(self, *args, **kwargs):
        super(BaseBleakScanner, self).__init__()
        self._callback: Optional[Callable[[AdvertisementData], None]] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    @classmethod
    async def discover(cls, timeout=5.0, **kwargs) -> List[BLEDevice]:
        """Scan continuously for ``timeout`` seconds and return discovered devices.

        Args:
            timeout: Time to scan for.

        Keyword Args:
            **kwargs: Implementations might offer additional keyword arguments sent to the constructor of the
                      BleakScanner class.

        Returns:

        """
        async with cls(**kwargs) as scanner:
            await asyncio.sleep(timeout)
            devices = await scanner.get_discovered_devices()
        return devices

    def register_detection_callback(
        self, callback: Optional[Callable[[AdvertisementData], None]]
    ) -> None:
        """Register a callback that is called when a device is discovered or has a property changed.

        If another callback has already been registered, it will be replaced with ``callback``.

        Args:
            callback: A function that takes one argument which will be an :class:`AdvertisementData` object
                      or ``None`` remove an existing callback.
        """
        self._callback = callback

    @abc.abstractmethod
    async def start(self):
        """Start scanning for devices"""
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop(self):
        """Stop scanning for devices"""
        raise NotImplementedError()

    @abc.abstractmethod
    async def set_scanning_filter(self, **kwargs):
        """Set scanning filter for the BleakScanner.

        Args:
            **kwargs: The filter details. This will differ a lot between backend implementations.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_discovered_devices(self) -> List[BLEDevice]:
        """Gets the devices registered by the BleakScanner.

        Returns:
            A list of the devices that the scanner has discovered during the scanning.

        """
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    async def find_device_by_address(
        cls, device_identifier: str, timeout: float = 10.0
    ) -> BLEDevice:
        """A convenience method for obtaining a ``BLEDevice`` object specified by Bluetooth address or (macOS) UUID address.

        Args:
            device_identifier (str): The Bluetooth/UUID address of the Bluetooth peripheral sought.
            timeout (float): Optional timeout to wait for detection of specified peripheral before giving up. Defaults to 10.0 seconds.

        Returns:
            The ``BLEDevice`` sought or ``None`` if not detected.

        """
        raise NotImplementedError()

    async def _find_device_by_address(
        self, device_identifier, stop_scanning_event, stop_if_detected_callback, timeout
    ):
        """Internal method for performing find by address work."""

        self.register_detection_callback(stop_if_detected_callback)

        await self.start()
        try:
            await asyncio.wait_for(stop_scanning_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            device = None
        else:
            device = next(
                d
                for d in await self.get_discovered_devices()
                if d.address.lower() == device_identifier.lower()
            )
        finally:
            await self.stop()

        return device
