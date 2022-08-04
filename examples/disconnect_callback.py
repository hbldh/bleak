"""
Disconnect callback
-------------------

An example showing how the `set_disconnected_callback` can be used on BlueZ backend.

Updated on 2019-09-07 by hbldh <henrik.blidh@gmail.com>

"""

import asyncio

from bleak import BleakClient, BleakScanner


async def main():
    devs = await BleakScanner.discover()
    if not devs:
        print("No devices found, try again later.")
        return

    disconnected_event = asyncio.Event()

    def disconnected_callback(client):
        print("Disconnected callback called!")
        disconnected_event.set()

    async with BleakClient(
        devs[0], disconnected_callback=disconnected_callback
    ) as client:
        print("Sleeping until device disconnects...")
        await disconnected_event.wait()
        print("Connected:", client.is_connected)


if __name__ == "__main__":
    asyncio.run(main())
