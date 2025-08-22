# -*- coding: utf-8 -*-
# Created on 2019-03-19 by hbldh <henrik.blidh@nedomkull.com>
"""
Interface class for the Bleak representation of a GATT Characteristic
"""
from __future__ import annotations

import enum
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Union
from uuid import UUID

from bleak.assigned_numbers import CharacteristicPropertyName
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.uuids import normalize_uuid_str, uuidstr_to_str

# to prevent circular import
if TYPE_CHECKING:
    from bleak.backends.service import BleakGATTService


class GattCharacteristicsFlags(enum.Enum):
    broadcast = 0x0001
    read = 0x0002
    write_without_response = 0x0004
    write = 0x0008
    notify = 0x0010
    indicate = 0x0020
    authenticated_signed_writes = 0x0040
    extended_properties = 0x0080
    reliable_write = 0x0100
    writable_auxiliaries = 0x0200


class BleakGATTCharacteristic:
    """The Bleak representation of a GATT Characteristic"""

    def __init__(
        self,
        obj: Any,
        handle: int,
        uuid: str,
        properties: list[CharacteristicPropertyName],
        max_write_without_response_size: Callable[[], int],
        service: BleakGATTService,
    ):
        """
        Args:
            obj:
                A platform-specific object for this characteristic.
            max_write_without_response_size:
                The maximum size in bytes that can be written to the
                characteristic in a single write without response command.
            service:
                The service this characteristic belongs to.
        """
        self.obj = obj
        self._handle = handle
        self._uuid = uuid
        self._properties = properties
        self._max_write_without_response_size = max_write_without_response_size
        self._service = service
        self._descriptors: dict[int, BleakGATTDescriptor] = {}

    def __str__(self):
        return f"{self.uuid} (Handle: {self.handle}): {self.description}"

    @property
    def service_uuid(self) -> str:
        """The UUID of the Service containing this characteristic"""
        return self._service.uuid

    @property
    def service_handle(self) -> int:
        """The integer handle of the Service containing this characteristic"""
        return self._service.handle

    @property
    def handle(self) -> int:
        """The handle for this characteristic"""
        return self._handle

    @property
    def uuid(self) -> str:
        """The UUID for this characteristic"""
        return self._uuid

    @property
    def description(self) -> str:
        """Description for this characteristic"""
        return uuidstr_to_str(self.uuid)

    @property
    def properties(self) -> list[CharacteristicPropertyName]:
        """Properties of this characteristic"""
        return self._properties

    @property
    def max_write_without_response_size(self) -> int:
        """
        Gets the maximum size in bytes that can be used for the *data* argument
        of :meth:`BleakClient.write_gatt_char()` when ``response=False``.

        In rare cases, a device may take a long time to update this value, so
        reading this property may return the default value of ``20`` and reading
        it again after a some time may return the expected higher value.

        If you *really* need to wait for a higher value, you can do something
        like this:

        .. code-block:: python

            async with asyncio.timeout(10):
                while char.max_write_without_response_size == 20:
                    await asyncio.sleep(0.5)

        .. warning:: Linux quirk: For BlueZ versions < 5.62, this property
            will always return ``20``.

        .. versionadded:: 0.16
        """

        # for backwards compatibility
        if isinstance(self._max_write_without_response_size, int):
            return self._max_write_without_response_size

        return self._max_write_without_response_size()

    @property
    def descriptors(self) -> list[BleakGATTDescriptor]:
        """List of descriptors for this service"""
        return list(self._descriptors.values())

    def get_descriptor(
        self, specifier: Union[int, str, UUID]
    ) -> Union[BleakGATTDescriptor, None]:
        """Get a descriptor by handle (int) or UUID (str or uuid.UUID)"""
        if isinstance(specifier, int):
            return self._descriptors.get(specifier)

        uuid = normalize_uuid_str(str(specifier))
        for descriptor in self._descriptors.values():
            if descriptor.uuid == uuid:
                return descriptor

        return None

    def add_descriptor(self, descriptor: BleakGATTDescriptor) -> None:
        """Add a :py:class:`~BleakGATTDescriptor` to the characteristic.

        Should not be used by end user, but rather by `bleak` itself.
        """
        if descriptor.handle in self._descriptors:
            raise ValueError(
                f"Descriptor with handle {descriptor.handle} already exists"
            )

        self._descriptors[descriptor.handle] = descriptor
