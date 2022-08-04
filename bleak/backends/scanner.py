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
from bleak.abstract_api import AdvertisementDataCallback, AdvertisementDataFilter
from bleak import abstract_api


class AdvertisementData(abstract_api.AdvertisementData):
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


class BaseBleakScanner(abstract_api.AbstractBleakScanner):
    """Interface for Bleak Bluetooth LE Scanners, backend base class.

    A BleakScanner can be used as an asynchronous context manager in which case it automatically
    starts and stops scanning.

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
