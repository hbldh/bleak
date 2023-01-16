import collections
from ..descriptor import BleakGATTDescriptor

PartialDescriptor = collections.namedtuple("PartialDescriptor", ["uuid", "handle"])


class BleakGATTDescriptorBGAPI(BleakGATTDescriptor):
    """GATT Descriptor implementation for Silicon Labs BGAPI backend"""

    def __init__(
        self,
        obj: PartialDescriptor,
        characteristic_uuid: str,
        characteristic_handle: int,
    ):
        super(BleakGATTDescriptorBGAPI, self).__init__(obj)
        self.__characteristic_uuid = characteristic_uuid
        self.__characteristic_handle = characteristic_handle

    @property
    def characteristic_handle(self) -> int:
        """Handle for the characteristic that this descriptor belongs to"""
        return self.__characteristic_handle

    @property
    def characteristic_uuid(self) -> str:
        """UUID for the characteristic that this descriptor belongs to"""
        return self.__characteristic_uuid

    @property
    def uuid(self) -> str:
        """UUID for this descriptor"""
        return self.obj.uuid

    @property
    def handle(self) -> int:
        """Integer handle for this descriptor"""
        return self.obj.handle
