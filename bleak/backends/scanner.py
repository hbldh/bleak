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
        async with cls(**kwargs) as scanner:
            await asyncio.sleep(timeout)
            devices = await scanner.get_discovered_devices()
        return devices

    @abc.abstractmethod
    def register_detection_callback(self, callback: Callable):
        raise NotImplementedError()

    @abc.abstractmethod
    async def start(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def set_scanning_filter(self, **kwargs):
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_discovered_devices(self) -> List[BLEDevice]:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    async def find_specific_device(cls, device_identifier: str, timeout: float = 10.0) -> BLEDevice:
        """A convenience method for obtaining a ``BLEDevice`` object specified by MAC address or (macOS) UUID address.

        Args:
            device_identifier (str): The MAC/UUID address of the Bluetooth peripheral sought.
            timeout (float): Optional timeout to maximally wait for detection of specified peripheral. Defaults to 10.0 seconds.

        Returns:
            The ``BLEDevice`` sought or ``None`` if not detected.

        """
        raise NotImplementedError()
