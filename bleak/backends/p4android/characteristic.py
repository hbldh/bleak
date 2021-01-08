from uuid import UUID
from typing import Union, List

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.exc import BleakError

from jnius import autoclass


class _java:
    BluetoothGattCharacteristic = autoclass(
        "android.bluetooth.BluetoothGattCharacteristic"
    )

    CHARACTERISTIC_PROPERTY_DBUS_NAMES = {
        BluetoothGattCharacteristic.PROPERTY_BROADCAST: "broadcast",
        BluetoothGattCharacteristic.PROPERTY_EXTENDED_PROPS: "extended-properties",
        BluetoothGattCharacteristic.PROPERTY_INDICATE: "indicate",
        BluetoothGattCharacteristic.PROPERTY_NOTIFY: "notify",
        BluetoothGattCharacteristic.PROPERTY_READ: "read",
        BluetoothGattCharacteristic.PROPERTY_SIGNED_WRITE: "authenticated-signed-writes",
        BluetoothGattCharacteristic.PROPERTY_WRITE: "write",
        BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE: "write-without-response",
    }

    NOTIFICATION_DESCRIPTOR_UUID = "00002902-0000-1000-8000-00805f9b34fb"


class BleakGATTCharacteristicP4Android(BleakGATTCharacteristic):
    """GATT Characteristic implementation for the python-for-android backend"""

    def __init__(self, java, service_uuid: str):
        super(BleakGATTCharacteristicP4Android, self).__init__(java)
        self.__uuid = self.obj.getUuid().toString()
        self.__handle = self.obj.getInstanceId()
        self.__service_uuid = service_uuid
        self.__descriptors = []
        self.__notification_descriptor = None

        self.__properties = [
            name
            for flag, name in _java.CHARACTERISTIC_PROPERTY_DBUS_NAMES.items()
            if flag & self.obj.getProperties()
        ]

    @property
    def service_uuid(self) -> str:
        """The uuid of the Service containing this characteristic"""
        return self.__service_uuid

    @property
    def handle(self) -> int:
        """The handle of this characteristic"""
        return self.__handle

    @property
    def uuid(self) -> str:
        """The uuid of this characteristic"""
        return self.__uuid

    @property
    def properties(self) -> List:
        """Properties of this characteristic"""
        return self.__properties

    @property
    def descriptors(self) -> List:
        """List of descriptors for this service"""
        return self.__descriptors

    def get_descriptor(
        self, specifier: Union[str, UUID]
    ) -> Union[BleakGATTDescriptor, None]:
        """Get a descriptor by UUID (str or uuid.UUID)"""
        if isinstance(specifier, int):
            raise BleakError(
                "The Android Bluetooth API does not provide access to descriptor handles."
            )

        matches = [
            descriptor
            for descriptor in self.descriptors
            if descriptor.uuid == str(specifier)
        ]
        if len(matches) == 0:
            return None
        return matches[0]

    def add_descriptor(self, descriptor: BleakGATTDescriptor):
        """Add a :py:class:`~BleakGATTDescriptor` to the characteristic.

        Should not be used by end user, but rather by `bleak` itself.
        """
        self.__descriptors.append(descriptor)
        if descriptor.uuid == _java.NOTIFICATION_DESCRIPTOR_UUID:
            self.__notification_descriptor = descriptor

    @property
    def notification_descriptor(self) -> BleakGATTDescriptor:
        """The notification descriptor.  Mostly needed by `bleak`, not by end user"""
        return self.__notification_descriptor
