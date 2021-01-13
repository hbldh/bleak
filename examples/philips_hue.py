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

Created on 2020-01-13 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
import logging

from bleak import BleakClient


LIGHT_CHARACTERISTIC = "932c32bd-0002-47a2-835a-a8d455b859dd"
BRIGHTNESS_CHARACTERISTIC = "932c32bd-0003-47a2-835a-a8d455b859dd"
COLOR_CHARACTERISTIC = "932c32bd-0004-47a2-835a-a8d455b859dd"


async def run(address, debug=False):
    log = logging.getLogger(__name__)
    if debug:
        import sys

        log.setLevel(logging.DEBUG)
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.DEBUG)
        log.addHandler(h)

    async with BleakClient(address) as client:
        x = await client.is_connected()
        log.info("Connected: {0}".format(x))
        x = await client.pair(protection_level=2)
        log.info("Paired: {0}".format(x))

        print("Turning Light off...")
        await client.write_gatt_char(LIGHT_CHARACTERISTIC, b"\x00")
        await asyncio.sleep(1.0)
        print("Turning Light on...")
        await client.write_gatt_char(LIGHT_CHARACTERISTIC, b"\x01")
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
        )


if __name__ == "__main__":
    address = "EB:F0:49:21:95:4F"
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    loop.run_until_complete(run(address, True))
