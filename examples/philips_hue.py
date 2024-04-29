"""
Philips Hue lamp
----------------

Very important:

It seems that the device needs to be connected to in the official Philips Hue Bluetooth app
and reset from there to be able to use with Bleak-type of BLE software. After that one needs to
do a encrypted pairing to enable reading and writing of characteristics.

ONLY TESTED IN WINDOWS BACKEND AS OF YET!

References:

- https://www.reddit.com/r/Hue/comments/eq0y3y/philips_hue_bluetooth_developer_documentation/
- https://gist.github.com/shinyquagsire23/f7907fdf6b470200702e75a30135caf3
- https://github.com/Mic92/hue-ble-ctl/blob/master/hue-ble-ctl.py
- https://github.com/npaun/philble/blob/master/philble/client.py
- https://github.com/eb3095/hue-sync/blob/main/huelib/HueDevice.py

Created on 2020-01-13 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
import sys

from bleak import BleakClient

ADDRESS = "EB:F0:49:21:95:4F"

LIGHT_CHARACTERISTIC = "932c32bd-0002-47a2-835a-a8d455b859dd"
BRIGHTNESS_CHARACTERISTIC = "932c32bd-0003-47a2-835a-a8d455b859dd"
TEMPERATURE_CHARACTERISTIC = "932c32bd-0004-47a2-835a-a8d455b859dd"
COLOR_CHARACTERISTIC = "932c32bd-0005-47a2-835a-a8d455b859dd"


def convert_rgb(rgb):
    scale = 0xFF
    adjusted = [max(1, chan) for chan in rgb]
    total = sum(adjusted)
    adjusted = [int(round(chan / total * scale)) for chan in adjusted]

    # Unknown, Red, Blue, Green
    return bytearray([0x1, adjusted[0], adjusted[2], adjusted[1]])


async def main(address):
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")

        paired = await client.pair(protection_level=2)
        print(f"Paired: {paired}")

        print("Turning Light off...")
        await client.write_gatt_char(LIGHT_CHARACTERISTIC, b"\x00", response=False)
        await asyncio.sleep(1.0)
        print("Turning Light on...")
        await client.write_gatt_char(LIGHT_CHARACTERISTIC, b"\x01", response=False)
        await asyncio.sleep(1.0)

        print("Setting color to RED...")
        color = convert_rgb([255, 0, 0])
        await client.write_gatt_char(COLOR_CHARACTERISTIC, color, response=False)
        await asyncio.sleep(1.0)

        print("Setting color to GREEN...")
        color = convert_rgb([0, 255, 0])
        await client.write_gatt_char(COLOR_CHARACTERISTIC, color, response=False)
        await asyncio.sleep(1.0)

        print("Setting color to BLUE...")
        color = convert_rgb([0, 0, 255])
        await client.write_gatt_char(COLOR_CHARACTERISTIC, color, response=False)
        await asyncio.sleep(1.0)

        for brightness in range(256):
            print(f"Set Brightness to {brightness}...")
            await client.write_gatt_char(
                BRIGHTNESS_CHARACTERISTIC,
                bytearray(
                    [
                        brightness,
                    ]
                ),
                response=False,
            )
            await asyncio.sleep(0.2)

        print(f"Set Brightness to {40}...")
        await client.write_gatt_char(
            BRIGHTNESS_CHARACTERISTIC,
            bytearray(
                [
                    40,
                ]
            ),
            response=False,
        )


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) == 2 else ADDRESS))
