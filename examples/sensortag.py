# -*- coding: utf-8 -*-
"""
TI CC2650 SensorTag
-------------------

An example connecting to a TI CC2650 SensorTag.

Created on 2018-01-10 by hbldh <henrik.blidh@nedomkull.com>

"""
import asyncio
import platform
import sys

from bleak import BleakClient
from bleak.uuids import normalize_uuid_16, uuid16_dict

ADDRESS = (
    "24:71:89:cc:09:05"
    if platform.system() != "Darwin"
    else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
)

ALL_SENSORTAG_CHARACTERISTIC_UUIDS = """
00002a00-0000-1000-8000-00805f9b34fb
00002a01-0000-1000-8000-00805f9b34fb
00002a04-0000-1000-8000-00805f9b34fb
00002a23-0000-1000-8000-00805f9b34fb
00002a24-0000-1000-8000-00805f9b34fb
00002a25-0000-1000-8000-00805f9b34fb
00002a26-0000-1000-8000-00805f9b34fb
00002a27-0000-1000-8000-00805f9b34fb
00002a28-0000-1000-8000-00805f9b34fb
00002a29-0000-1000-8000-00805f9b34fb
00002a2a-0000-1000-8000-00805f9b34fb
00002a50-0000-1000-8000-00805f9b34fb
00002a19-0000-1000-8000-00805f9b34fb
f000aa01-0451-4000-b000-000000000000
f000aa02-0451-4000-b000-000000000000
f000aa03-0451-4000-b000-000000000000
f000aa21-0451-4000-b000-000000000000
f000aa22-0451-4000-b000-000000000000
f000aa23-0451-4000-b000-000000000000
f000aa41-0451-4000-b000-000000000000
f000aa42-0451-4000-b000-000000000000
f000aa44-0451-4000-b000-000000000000
f000aa81-0451-4000-b000-000000000000
f000aa82-0451-4000-b000-000000000000
f000aa83-0451-4000-b000-000000000000
f000aa71-0451-4000-b000-000000000000
f000aa72-0451-4000-b000-000000000000
f000aa73-0451-4000-b000-000000000000
0000ffe1-0000-1000-8000-00805f9b34fb
f000aa65-0451-4000-b000-000000000000
f000aa66-0451-4000-b000-000000000000
f000ac01-0451-4000-b000-000000000000
f000ac02-0451-4000-b000-000000000000
f000ac03-0451-4000-b000-000000000000
f000ccc1-0451-4000-b000-000000000000
f000ccc2-0451-4000-b000-000000000000
f000ccc3-0451-4000-b000-000000000000
f000ffc1-0451-4000-b000-000000000000
f000ffc2-0451-4000-b000-000000000000
f000ffc3-0451-4000-b000-000000000000
f000ffc4-0451-4000-b000-000000000000
"""

uuid16_lookup = {v: normalize_uuid_16(k) for k, v in uuid16_dict.items()}

SYSTEM_ID_UUID = uuid16_lookup["System ID"]
MODEL_NBR_UUID = uuid16_lookup["Model Number String"]
DEVICE_NAME_UUID = uuid16_lookup["Device Name"]
FIRMWARE_REV_UUID = uuid16_lookup["Firmware Revision String"]
HARDWARE_REV_UUID = uuid16_lookup["Hardware Revision String"]
SOFTWARE_REV_UUID = uuid16_lookup["Software Revision String"]
MANUFACTURER_NAME_UUID = uuid16_lookup["Manufacturer Name String"]
BATTERY_LEVEL_UUID = uuid16_lookup["Battery Level"]
KEY_PRESS_UUID = normalize_uuid_16(0xFFE1)
# I/O test points on SensorTag.
IO_DATA_CHAR_UUID = "f000aa65-0451-4000-b000-000000000000"
IO_CONFIG_CHAR_UUID = "f000aa66-0451-4000-b000-000000000000"


async def main(address):
    async with BleakClient(address, winrt=dict(use_cached_services=True)) as client:
        print(f"Connected: {client.is_connected}")

        system_id = await client.read_gatt_char(SYSTEM_ID_UUID)
        print(
            "System ID: {0}".format(
                ":".join(["{:02x}".format(x) for x in system_id[::-1]])
            )
        )

        model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        print("Model Number: {0}".format("".join(map(chr, model_number))))

        try:
            device_name = await client.read_gatt_char(DEVICE_NAME_UUID)
            print("Device Name: {0}".format("".join(map(chr, device_name))))
        except Exception:
            pass

        manufacturer_name = await client.read_gatt_char(MANUFACTURER_NAME_UUID)
        print("Manufacturer Name: {0}".format("".join(map(chr, manufacturer_name))))

        firmware_revision = await client.read_gatt_char(FIRMWARE_REV_UUID)
        print("Firmware Revision: {0}".format("".join(map(chr, firmware_revision))))

        hardware_revision = await client.read_gatt_char(HARDWARE_REV_UUID)
        print("Hardware Revision: {0}".format("".join(map(chr, hardware_revision))))

        software_revision = await client.read_gatt_char(SOFTWARE_REV_UUID)
        print("Software Revision: {0}".format("".join(map(chr, software_revision))))

        battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
        print("Battery Level: {0}%".format(int(battery_level[0])))

        async def notification_handler(characteristic, data):
            print(f"{characteristic.description}: {data}")

        # Turn on the red light on the Sensor Tag by writing to I/O Data and I/O Config.
        write_value = bytearray([0x01])
        value = await client.read_gatt_char(IO_DATA_CHAR_UUID)
        print("I/O Data Pre-Write Value: {0}".format(value))

        await client.write_gatt_char(IO_DATA_CHAR_UUID, write_value, response=True)

        value = await client.read_gatt_char(IO_DATA_CHAR_UUID)
        print("I/O Data Post-Write Value: {0}".format(value))
        assert value == write_value

        write_value = bytearray([0x01])
        value = await client.read_gatt_char(IO_CONFIG_CHAR_UUID)
        print("I/O Config Pre-Write Value: {0}".format(value))

        await client.write_gatt_char(IO_CONFIG_CHAR_UUID, write_value, response=True)

        value = await client.read_gatt_char(IO_CONFIG_CHAR_UUID)
        print("I/O Config Post-Write Value: {0}".format(value))
        assert value == write_value

        # Try notifications with key presses.

        await client.start_notify(KEY_PRESS_UUID, notification_handler)
        await asyncio.sleep(5.0)
        await client.stop_notify(KEY_PRESS_UUID)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) == 2 else ADDRESS))
