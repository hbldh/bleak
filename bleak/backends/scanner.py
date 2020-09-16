import abc
import asyncio
from typing import Callable, List

from bleak.backends.device import BLEDevice


class BaseBleakScanner(abc.ABC):
    """Interface for Bleak Bluetooth LE Scanners"""

    def __init__(self, *args, **kwargs):
        super(BaseBleakScanner, self).__init__()

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

    @abc.abstractmethod
    def register_detection_callback(self, callback: Callable):
        """Register a callback that is called when a device is discovered or has a property changed."""
        raise NotImplementedError()

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
