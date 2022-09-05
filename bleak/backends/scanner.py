import abc
import asyncio
import inspect
import os
import platform
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Type

from ..exc import BleakError
from .device import BLEDevice


class AdvertisementData:
    """
    Wrapper around the advertisement data that each platform returns upon discovery
    """

    def __init__(self, **kwargs):
        """
        Keyword Args:
            local_name (str): The name of the ble device advertising
            manufacturer_data (dict): Manufacturer data from the device
            service_data (dict): Service data from the device
            service_uuids (list): UUIDs associated with the device
            platform_data (tuple): Tuple of platform specific advertisement data
            tx_power (int): Transmit power level of the device
        """
        # The local name of the device
        self.local_name: Optional[str] = kwargs.get("local_name", None)

        # Dictionary of manufacturer data in bytes
        self.manufacturer_data: Dict[int, bytes] = kwargs.get("manufacturer_data", {})

        # Dictionary of service data
        self.service_data: Dict[str, bytes] = kwargs.get("service_data", {})

        # List of UUIDs
        self.service_uuids: List[str] = kwargs.get("service_uuids", [])

        # Tuple of platform specific data
        self.platform_data: Tuple = kwargs.get("platform_data", ())

        # Tx Power data
        self.tx_power: Optional[int] = kwargs.get("tx_power")

    def __repr__(self) -> str:
        kwargs = []
        if self.local_name:
            kwargs.append(f"local_name={repr(self.local_name)}")
        if self.manufacturer_data:
            kwargs.append(f"manufacturer_data={repr(self.manufacturer_data)}")
        if self.service_data:
            kwargs.append(f"service_data={repr(self.service_data)}")
        if self.service_uuids:
            kwargs.append(f"service_uuids={repr(self.service_uuids)}")
        if self.tx_power is not None:
            kwargs.append(f"tx_power={repr(self.tx_power)}")
        return f"AdvertisementData({', '.join(kwargs)})"


AdvertisementDataCallback = Callable[
    [BLEDevice, AdvertisementData],
    Optional[Awaitable[None]],
]

AdvertisementDataFilter = Callable[
    [BLEDevice, AdvertisementData],
    bool,
]


class BaseBleakScanner(abc.ABC):
    """
    Interface for Bleak Bluetooth LE Scanners

    Args:
        detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
        service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received.
    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback],
        service_uuids: Optional[List[str]],
    ):
        super(BaseBleakScanner, self).__init__()
        self._callback: Optional[AdvertisementDataCallback] = None
        self.register_detection_callback(detection_callback)
        self._service_uuids: Optional[List[str]] = (
            [u.lower() for u in service_uuids] if service_uuids is not None else None
        )

    def register_detection_callback(
        self, callback: Optional[AdvertisementDataCallback]
    ) -> None:
        """Register a callback that is called when a device is discovered or has a property changed.

        If another callback has already been registered, it will be replaced with ``callback``.
        ``None`` can be used to remove the current callback.

        The ``callback`` is a function or coroutine that takes two arguments: :class:`BLEDevice`
        and :class:`AdvertisementData`.

        Args:
            callback: A function, coroutine or ``None``.

        """
        if callback is not None:
            error_text = "callback must be callable with 2 parameters"
            if not callable(callback):
                raise TypeError(error_text)

            handler_signature = inspect.signature(callback)
            if len(handler_signature.parameters) != 2:
                raise TypeError(error_text)

        if inspect.iscoroutinefunction(callback):

            def detection_callback(s, d):
                asyncio.ensure_future(callback(s, d))

        else:
            detection_callback = callback

        self._callback = detection_callback

    @abc.abstractmethod
    async def start(self):
        """Start scanning for devices"""
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop(self):
        """Stop scanning for devices"""
        raise NotImplementedError()

    @abc.abstractmethod
    def set_scanning_filter(self, **kwargs):
        """Set scanning filter for the BleakScanner.

        Args:
            **kwargs: The filter details. This will differ a lot between backend implementations.

        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def discovered_devices(self) -> List[BLEDevice]:
        """Gets the devices registered by the BleakScanner.

        Returns:
            A list of the devices that the scanner has discovered during the scanning.
        """
        raise NotImplementedError()


def get_platform_scanner_backend_type() -> Type[BaseBleakScanner]:
    """
    Gets the platform-specific :class:`BaseBleakScanner` type.
    """
    if os.environ.get("P4A_BOOTSTRAP") is not None:
        from bleak.backends.p4android.scanner import BleakScannerP4Android

        return BleakScannerP4Android

    if platform.system() == "Linux":
        from bleak.backends.bluezdbus.scanner import BleakScannerBlueZDBus

        return BleakScannerBlueZDBus

    if platform.system() == "Darwin":
        from bleak.backends.corebluetooth.scanner import BleakScannerCoreBluetooth

        return BleakScannerCoreBluetooth

    if platform.system() == "Windows":
        from bleak.backends.winrt.scanner import BleakScannerWinRT

        return BleakScannerWinRT

    raise BleakError(f"Unsupported platform: {platform.system()}")
