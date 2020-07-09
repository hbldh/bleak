import abc
import asyncio
from typing import Callable, List

from bleak.backends.device import BLEDevice


class BaseBleakScanner(abc.ABC):
    """Interface for Bleak Bluetooth LE Scanners"""

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    @classmethod
    async def discover(cls, timeout=5.0, **kwargs) -> List[BLEDevice]:
        async with cls(**kwargs) as scanner:
            await asyncio.sleep(timeout if timeout > 0.0 else 0.1)
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
