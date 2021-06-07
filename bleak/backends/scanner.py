import abc
import asyncio
import inspect
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)
from warnings import warn

from bleak.backends.device import BLEDevice


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
    """Interface for Bleak Bluetooth LE Scanners"""

    def __init__(self, *args, **kwargs):
        super(BaseBleakScanner, self).__init__()
        self._callback: Optional[AdvertisementDataCallback] = None
        self.register_detection_callback(kwargs.get("detection_callback"))

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
            devices = scanner.discovered_devices
        return devices

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

    @abc.abstractproperty
    def discovered_devices(self) -> List[BLEDevice]:
        """Gets the devices registered by the BleakScanner.

        Returns:
            A list of the devices that the scanner has discovered during the scanning.
        """
        raise NotImplementedError()

    async def get_discovered_devices(self) -> List[BLEDevice]:
        """Gets the devices registered by the BleakScanner.

        .. deprecated:: 0.11.0
            This method will be removed in a future version of Bleak. Use the
            :attr:`.discovered_devices` property instead.

        Returns:
            A list of the devices that the scanner has discovered during the scanning.

        """
        warn(
            "This method will be removed in a future version of Bleak. Use the `discovered_devices` property instead.",
            FutureWarning,
            stacklevel=2,
        )
        return self.discovered_devices

    @classmethod
    async def find_device_by_address(
        cls, device_identifier: str, timeout: float = 10.0, **kwargs
    ) -> Optional[BLEDevice]:
        """A convenience method for obtaining a ``BLEDevice`` object specified by Bluetooth address or (macOS) UUID address.

        Args:
            device_identifier (str): The Bluetooth/UUID address of the Bluetooth peripheral sought.
            timeout (float): Optional timeout to wait for detection of specified peripheral before giving up. Defaults to 10.0 seconds.

        Keyword Args:
            adapter (str): Bluetooth adapter to use for discovery.

        Returns:
            The ``BLEDevice`` sought or ``None`` if not detected.

        """
        device_identifier = device_identifier.lower()
        return await cls.find_device_by_filter(
            lambda d, ad: d.address.lower() == device_identifier
        )

    @classmethod
    async def find_device_by_filter(
        cls, filterfunc: AdvertisementDataFilter, timeout: float = 10.0, **kwargs
    ) -> Optional[BLEDevice]:
        """A convenience method for obtaining a ``BLEDevice`` object specified by a filter function.

        Args:
            filterfunc (AdvertisementDataFilter): A function that is called for every BLEDevice found. It should return True only for the wanted device.
            timeout (float): Optional timeout to wait for detection of specified peripheral before giving up. Defaults to 10.0 seconds.

        Keyword Args:
            adapter (str): Bluetooth adapter to use for discovery.

        Returns:
            The ``BLEDevice`` sought or ``None`` if not detected.

        """
        found_device_queue = asyncio.Queue()

        def apply_filter(d: BLEDevice, ad: AdvertisementData):
            if filterfunc(d, ad):
                found_device_queue.put_nowait(d)

        async with cls(detection_callback=apply_filter, **kwargs):
            try:
                return await asyncio.wait_for(found_device_queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                return None
