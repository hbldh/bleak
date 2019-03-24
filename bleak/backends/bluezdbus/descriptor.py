from bleak.backends.descriptor import BleakGATTDescriptor


class BleakGATTDescriptorBlueZDBus(BleakGATTDescriptor):
    def __init__(self, obj: dict, object_path: str, characteristic_uuid: str):
        super(BleakGATTDescriptorBlueZDBus, self).__init__(obj)
        self.__path = object_path
        self.__characteristic_uuid = characteristic_uuid
        self.__handle = int(self.path.split("/")[-1].replace("desc", ""), 16)

    @property
    def characteristic_uuid(self) -> str:
        return self.__characteristic_uuid

    @property
    def uuid(self) -> str:
        return self.obj["UUID"]

    @property
    def handle(self) -> int:
        return self.__handle

    @property
    def path(self) -> str:
        return self.__path
