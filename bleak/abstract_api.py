# -*- coding: utf-8 -*-
"""
Gatt Service Collection class and interface class for the Bleak representation of a GATT Service.

Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import abc
import uuid
from uuid import UUID
from typing import Dict, List, Optional, Union, Iterator, Any, Callable
from bleak import BleakError
from bleak.uuids import uuidstr_to_str


class BleakGATTDescriptor(abc.ABC):
    """Interface for the Bleak representation of a GATT Descriptor"""

    def __init__(self, obj: Any):
        self.obj = obj

    def __str__(self):
        return f"{self.uuid} (Handle: {self.handle}): {self.description}"

    @property
    @abc.abstractmethod
    def characteristic_uuid(self) -> str:
        """UUID for the characteristic that this descriptor belongs to"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def characteristic_handle(self) -> int:
        """handle for the characteristic that this descriptor belongs to"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def uuid(self) -> str:
        """UUID for this descriptor"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def handle(self) -> int:
        """Integer handle for this descriptor"""
        raise NotImplementedError()

    @property
    def description(self) -> str:
        """A text description of what this descriptor represents"""
        raise NotImplementedError()


class BleakGATTCharacteristic(abc.ABC):
    """Interface for the Bleak representation of a GATT Characteristic"""

    def __init__(self, obj: Any):
        self.obj = obj

    def __str__(self):
        return f"{self.uuid} (Handle: {self.handle}): {self.description}"

    @property
    @abc.abstractmethod
    def service_uuid(self) -> str:
        """The UUID of the Service containing this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def service_handle(self) -> int:
        """The integer handle of the Service containing this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def handle(self) -> int:
        """The handle for this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def uuid(self) -> str:
        """The UUID for this characteristic"""
        raise NotImplementedError()

    @property
    def description(self) -> str:
        """Description for this characteristic"""
        return uuidstr_to_str(self.uuid)

    @property
    @abc.abstractmethod
    def properties(self) -> List[str]:
        """Properties of this characteristic"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def descriptors(self) -> List:
        """List of descriptors for this service"""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_descriptor(
        self, specifier: Union[int, str, UUID]
    ) -> Union[BleakGATTDescriptor, None]:
        """Get a descriptor by handle (int) or UUID (str or uuid.UUID)"""
        raise NotImplementedError()


class BleakGATTService(abc.ABC):
    """Interface for the Bleak representation of a GATT Service."""

    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        return f"{self.uuid} (Handle: {self.handle}): {self.description}"

    @property
    @abc.abstractmethod
    def handle(self) -> int:
        """The handle of this service"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def uuid(self) -> str:
        """The UUID of this service"""
        raise NotImplementedError()

    @property
    def description(self) -> str:
        """String description of this service"""
        return uuidstr_to_str(self.uuid)

    @property
    @abc.abstractmethod
    def characteristics(self) -> List[BleakGATTCharacteristic]:
        """List of characteristics for this service"""
        raise NotImplementedError()

    def get_characteristic(
        self, uuid: Union[str, UUID]
    ) -> Union[BleakGATTCharacteristic, None]:
        """Get a characteristic by UUID.

        :param uuid: The UUID to match.
        :returns: The first characteristic matching ``uuid`` or ``None`` if no
            matching characteristic was found.
        """
        if type(uuid) == str and len(uuid) == 4:
            # Convert 16-bit uuid to 128-bit uuid
            uuid = f"0000{uuid}-0000-1000-8000-00805f9b34fb"
        try:
            return next(
                filter(lambda x: x.uuid == str(uuid).lower(), self.characteristics)
            )
        except StopIteration:
            return None


class BleakGATTServiceCollection(abc.ABC):
    """Simple data container for storing the peripheral's service complement."""

    def __init__(self):
        self._services = {}
        self._characteristics = {}
        self._descriptors = {}

    def __getitem__(
        self, item: Union[str, int, UUID]
    ) -> Optional[
        Union[BleakGATTService, BleakGATTCharacteristic, BleakGATTDescriptor]
    ]:
        """Get a service, characteristic or descriptor from uuid or handle"""
        return (
            self.get_service(item)
            or self.get_characteristic(item)
            or self.get_descriptor(item)
        )

    def __iter__(self) -> Iterator[BleakGATTService]:
        """Returns an iterator over all BleakGATTService objects"""
        return iter(self.services.values())

    @property
    def services(self) -> Dict[int, BleakGATTService]:
        """Get all services.

        :returns: dictionary of handles mapping to BleakGATTService
        """
        return self._services

    @property
    def characteristics(self) -> Dict[int, BleakGATTCharacteristic]:
        """Get all characteristics of all services.

        :returns: dictionary of handles mapping to BleakGATTCharacteristic
        """
        return self._characteristics

    @property
    def descriptors(self) -> Dict[int, BleakGATTDescriptor]:
        """Get all descriptors of all characteristics of all services.

        :returns: dictionary of handles mapping to BleakGATTDescriptor"""
        return self._descriptors

    def get_service(
        self, specifier: Union[int, str, UUID]
    ) -> Optional[BleakGATTService]:
        """Get a single service.

        :param specifier: UUID or handle for the service to get
        :returns: The BleakGATTService object (or None if it does not exist)
        """
        if isinstance(specifier, int):
            return self.services.get(specifier)

        _specifier = str(specifier).lower()

        # Assume uuid usage.
        # Convert 16-bit uuid to 128-bit uuid
        if len(_specifier) == 4:
            _specifier = f"0000{_specifier}-0000-1000-8000-00805f9b34fb"

        x = list(
            filter(
                lambda x: x.uuid.lower() == _specifier,
                self.services.values(),
            )
        )

        if len(x) > 1:
            raise BleakError(
                "Multiple Services with this UUID, refer to your desired service by the `handle` attribute instead."
            )

        return x[0] if x else None

    def get_characteristic(
        self, specifier: Union[int, str, UUID]
    ) -> Optional[BleakGATTCharacteristic]:
        """Get a single characteristic.

        :param specifier: UUID or handle for the characteristic to get
        :returns: The BleakGATTService object (or None if it does not exist)
        """
        if isinstance(specifier, int):
            return self.characteristics.get(specifier)

        # Assume uuid usage.
        x = list(
            filter(
                lambda x: x.uuid == str(specifier).lower(),
                self.characteristics.values(),
            )
        )

        if len(x) > 1:
            raise BleakError(
                "Multiple Characteristics with this UUID, refer to your desired characteristic by the `handle` attribute instead."
            )

        return x[0] if x else None

    def get_descriptor(self, handle: int) -> Optional[BleakGATTDescriptor]:
        """Get a descriptor by integer handle"""
        return self.descriptors.get(handle)


class BLEDevice(abc.ABC):
    """Class representing a BLE server detected during a `discover` call."""

    #: BLE address of the server (in a backend-specific notation)
    address: str
    #: User-readable name the server announced in its advertisement
    name: str
    #: Backend-specific details of the server discovered from its advertisement
    details: Any
    #: Received Signal Strength Indicator, higher values mean the signal was stronger
    rssi: int
    #: Other data received from the server in its advertisement
    metadata: dict[str, Any]

    def __repr__(self):
        return str(self)


class AbstractBleakClient(abc.ABC):
    """API for connecting to a BLE server and communicating with it."""

    #: BLE address of the server
    address: Union[str, BLEDevice]
    #: Services and characteristics exported by the server
    services: BleakGATTServiceCollection

    # Async Context managers

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    # Connectivity methods

    def set_disconnected_callback(
        self, callback: Optional[Callable[["AbstractBleakClient"], None]], **kwargs
    ) -> None:
        """Set the disconnect callback.

        The callback will only be called on unsolicited disconnect event, with this BleakClient as parameter.

        :param callback: callback, or None to clear the disconnection callback
        """
        self._disconnected_callback = callback

    @abc.abstractmethod
    async def connect(self, **kwargs) -> bool:
        """Connect to the specified GATT server.

        This method may have backend-specific additional keyword arguments.

        :returns: true if succesful.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the specified GATT server.

        :returns: True if succesful
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def pair(self, *args, **kwargs) -> bool:
        """Pair with the server.

        This method may not be available (or needed) for some backends.
        This method may have backend-specific additional keyword arguments.

        :returns: True if succesful
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def unpair(self) -> bool:
        """Unpair with the server.

        :returns: True if succesful
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """True if we are currently connected to the server"""
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        """Get all services registered for this GATT server.

        This method may have backend-specific additional keyword arguments.

        Note that you should use this method in stead of directly accessing the
        services attribute, which may not be valid. Using this method will honour
        the caching settings specified.

        :returns: Description of all services and characteristics
        """
        raise NotImplementedError()

    # I/O methods

    @abc.abstractmethod
    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        **kwargs,
    ) -> bytearray:
        """Perform read operation on the specified GATT characteristic.

        This method may have backend-specific additional keyword arguments.

        :param char_specifier: The characteristic to read from ((BleakGATTCharacteristic, handle or UUID))
        :returns: The data read (bytearray without any conversion).

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def read_gatt_descriptor(self, handle: int, **kwargs) -> bytearray:
        """Perform read operation on the specified GATT descriptor.

        :param handle: The handle of the descriptor to read from.
        :returns: (bytearray) The read data.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        data: Union[bytes, bytearray, memoryview],
        response: bool = False,
    ) -> None:
        """Perform a write operation on the specified GATT characteristic.

        :param char_specifier: The characteristic to write to ((BleakGATTCharacteristic, handle or UUID))
        :param data: (bytes or bytearray): The data to send.
        :param response: If write-with-response operation should be done. Defaults to `False`.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def write_gatt_descriptor(
        self, handle: int, data: Union[bytes, bytearray, memoryview]
    ) -> None:
        """Perform a write operation on the specified GATT descriptor.

        :param handle: The handle of the descriptor to read from.
        :param data: (bytes or bytearray) The data to send.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def start_notify(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        callback: Callable[[int, bytearray], None],
        **kwargs,
    ) -> None:
        """Activate notifications/indications on a characteristic.

        When a notification or indication is received from the server the callback
        is called with two parameters: the handle of the characteristic to which it pertains
        and the data received.

        :param char_specifier: The characteristic to activate notifications/indications on
        :param callback: The function to be called on notification.

        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def stop_notify(
        self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID]
    ) -> None:
        """Deactivate notification/indication on a specified characteristic.

        :param char_specifier: The characteristic to deactivate notification/indication on
        """
        raise NotImplementedError()
