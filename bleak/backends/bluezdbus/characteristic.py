from uuid import UUID
from typing import Union, List

from bleak.backends.bluezdbus.utils import extract_service_handle_from_path
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor


_GattCharacteristicsFlagsEnum = {
    0x0001: "broadcast",
    0x0002: "read",
    0x0004: "write-without-response",
    0x0008: "write",
    0x0010: "notify",
    0x0020: "indicate",
    0x0040: "authenticated-signed-writes",
    0x0080: "extended-properties",
    0x0100: "reliable-write",
    0x0200: "writable-auxiliaries",
    # "encrypt-read"
    # "encrypt-write"
    # "encrypt-authenticated-read"
    # "encrypt-authenticated-write"
    # "secure-read" #(Server only)
    # "secure-write" #(Server only)
    # "authorize"
}


class BleakGATTCharacteristicBlueZDBus(BleakGATTCharacteristic):
    """GATT Characteristic implementation for the BlueZ DBus backend"""

    def __init__(
        self, obj: dict, object_path: str, service_uuid: str, service_handle: int
    ):
        """Should not be called by end user, only by bleak itself"""
        super(BleakGATTCharacteristicBlueZDBus, self).__init__(obj)
        self.__descriptors = []
        self.__path = object_path
        self.__service_uuid = service_uuid
        self.__service_handle = service_handle
        self._handle = extract_service_handle_from_path(object_path)

    @property
    def service_uuid(self) -> str:
        return self.__service_uuid

    @property
    def service_handle(self) -> int:
        return self.__service_handle

    @property
    def handle(self) -> int:
        return self._handle

    @property
    def uuid(self) -> str:
        return self.obj.get("UUID")

    @property
    def properties(self) -> List:
        """Properties of this characteristic

        Returns the characteristics `Flags` present in the DBus API.
        """
        return self.obj["Flags"]

    @property
    def descriptors(self) -> List:
        return self.__descriptors

    def get_descriptor(
        self, specifier: Union[int, str, UUID]
    ) -> Union[BleakGATTDescriptor, None]:
        try:
            if isinstance(specifier, int):
                return next(filter(lambda x: x.handle == specifier, self.descriptors))
            else:
                return next(
                    filter(lambda x: x.uuid == str(specifier), self.descriptors)
                )
        except StopIteration:
            return None

    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        self.__descriptors.append(descriptor)

    @property
    def path(self) -> str:
        """The DBus path. Mostly needed by `bleak`, not by end user"""
        return self.__path
