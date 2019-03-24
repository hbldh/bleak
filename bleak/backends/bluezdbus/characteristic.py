from typing import Union, List

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
    """Interface for the Bleak representation of a GATT Characteristic"""

    def __init__(self, obj: dict, object_path: str, service_uuid: str):
        super(BleakGATTCharacteristicBlueZDBus, self).__init__(obj)
        self.__descriptors = []
        self.__path = object_path
        self.__service_uuid = service_uuid

    @property
    def service_uuid(self) -> str:
        """The uuid of the Service containing this characteristic"""
        return self.__service_uuid

    @property
    def uuid(self) -> str:
        """The uuid of this characteristic"""
        return self.obj.get("UUID")

    @property
    def description(self) -> str:
        # No description available in DBus backend.
        return ""

    @property
    def properties(self) -> List:
        return self.obj["Flags"]

    @property
    def descriptors(self) -> List:
        return self.__descriptors

    def get_descriptor(self, _uuid: str) -> Union[BleakGATTDescriptor, None]:
        try:
            return next(filter(lambda x: x.uuid == _uuid, self.descriptors))
        except StopIteration:
            return None

    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        self.__descriptors.append(descriptor)

    @property
    def path(self) -> str:
        return self.__path
