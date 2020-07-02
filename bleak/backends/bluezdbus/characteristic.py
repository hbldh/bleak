import re
from uuid import UUID
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

_handle_regex = re.compile("/char([0-9a-fA-F]*)")


class BleakGATTCharacteristicBlueZDBus(BleakGATTCharacteristic):
    """GATT Characteristic implementation for the BlueZ DBus backend"""

    def __init__(self, obj: dict, object_path: str, service_uuid: str):
        super(BleakGATTCharacteristicBlueZDBus, self).__init__(obj)
        self.__descriptors = []
        self.__path = object_path
        self.__service_uuid = service_uuid

        # The `Handle` attribute is added in BlueZ Release 5.51. Empirically,
        # it seems to hold true that the "/charYYYY" that is at the end of the
        # DBUS path actually is the desired handle. Using regex to extract
        # that and using as handle, since handle is mostly used for keeping
        # track of characteristics (internally in bleak anyway).
        self._handle = self.obj.get("Handle")
        if not self._handle:
            _handle_from_path = _handle_regex.search(self.path)
            if _handle_from_path:
                self._handle = int(_handle_from_path.groups()[0], 16)
        self._handle = int(self._handle)

    @property
    def service_uuid(self) -> str:
        """The uuid of the Service containing this characteristic"""
        return self.__service_uuid

    @property
    def handle(self) -> int:
        """The handle of this characteristic"""
        return self._handle

    @property
    def uuid(self) -> str:
        """The uuid of this characteristic"""
        return self.obj.get("UUID")

    @property
    def description(self) -> str:
        """Description for this characteristic"""
        # No description available in DBus backend.
        return ""

    @property
    def properties(self) -> List:
        """Properties of this characteristic

        Returns the characteristics `Flags` present in the DBus API.
        """
        return self.obj["Flags"]

    @property
    def descriptors(self) -> List:
        """List of descriptors for this service"""
        return self.__descriptors

    def get_descriptor(
        self, specifier: Union[int, str, UUID]
    ) -> Union[BleakGATTDescriptor, None]:
        """Get a descriptor by handle (int) or UUID (str or uuid.UUID)"""
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
        """Add a :py:class:`~BleakGATTDescriptor` to the characteristic.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__descriptors.append(descriptor)

    @property
    def path(self) -> str:
        """The DBus path. Mostly needed by `bleak`, not by end user"""
        return self.__path
