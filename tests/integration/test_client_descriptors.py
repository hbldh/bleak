from bumble.device import Device
from bumble.gatt import (
    GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
    Characteristic,
    Descriptor,
    Service,
)

from bleak import BleakClient
from tests.integration.conftest import (
    configure_and_power_on_bumble_peripheral,
    find_ble_device,
)


async def test_read_gatt_descriptor(bumble_peripheral: Device):
    """Reading a GATT descriptor is possible."""
    READABLE_DESCRIPTOR_SERVICE_UUID = "0d15eded-4e68-4718-bedf-736847b68e72"
    READABLE_DESCRIPTOR_CHARACTERISITC_UUID = "25c614ab-1560-46da-94bc-c146addfc359"
    virtual_descriptor = Descriptor(
        GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
        Descriptor.READABLE,
        "Description".encode(),
    )
    virtual_characteristic = Characteristic(
        READABLE_DESCRIPTOR_CHARACTERISITC_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"",
        [virtual_descriptor],
    )
    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        services=[Service(READABLE_DESCRIPTOR_SERVICE_UUID, [virtual_characteristic])],
    )

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(
        device, services=[READABLE_DESCRIPTOR_SERVICE_UUID]
    ) as client:
        characteristic = client.services.get_characteristic(
            READABLE_DESCRIPTOR_CHARACTERISITC_UUID
        )
        assert characteristic

        descriptor = characteristic.get_descriptor(
            GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR.to_hex_str()
        )
        assert descriptor

        data = await client.read_gatt_descriptor(descriptor)
        assert data == b"Description"


async def test_write_gatt_descriptor(bumble_peripheral: Device):
    """Writing a GATT descriptor is possible."""
    WRITABLE_DESCRIPTOR_SERVICE_UUID = "bef6dc41-8986-4c32-b746-6e2b10ca06e0"
    WRITABLE_DESCRIPTOR_CHARACTERISITC_UUID = "822afd2f-c2b2-4302-9edb-09850a93b707"
    virtual_descriptor = Descriptor(
        GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR,
        Descriptor.WRITEABLE,
        b"-----------",
    )
    virtual_characteristic = Characteristic(
        WRITABLE_DESCRIPTOR_CHARACTERISITC_UUID,
        Characteristic.Properties.READ,
        Characteristic.Permissions.READABLE,
        b"",
        [virtual_descriptor],
    )
    await configure_and_power_on_bumble_peripheral(
        bumble_peripheral,
        services=[Service(WRITABLE_DESCRIPTOR_SERVICE_UUID, [virtual_characteristic])],
    )

    device = await find_ble_device(bumble_peripheral)

    async with BleakClient(
        device, services=[WRITABLE_DESCRIPTOR_SERVICE_UUID]
    ) as client:
        characteristic = client.services.get_characteristic(
            WRITABLE_DESCRIPTOR_CHARACTERISITC_UUID
        )
        assert characteristic

        descriptor = characteristic.get_descriptor(
            GATT_CHARACTERISTIC_USER_DESCRIPTION_DESCRIPTOR.to_hex_str()
        )
        assert descriptor

        await client.write_gatt_descriptor(descriptor, b"Description")
        assert virtual_descriptor.value == b"Description"  # type: ignore  # (missing type hints in bumble)
