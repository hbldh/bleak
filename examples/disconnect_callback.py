"""
Disconnect callback
-------------------

An example showing how the `set_disconnected_callback` can be used on BlueZ backend.

Updated on 2019-09-07 by hbldh <henrik.blidh@gmail.com>

"""

import asyncio

from bleak import BleakClient, discover


async def show_disconnect_handling():
    devs = await discover()
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


# It is important to use asyncio.run() to get proper cleanup on KeyboardInterrupt.
# This was introduced in Python 3.7. If you need it in Python 3.6, you can copy
# it from https://github.com/python/cpython/blob/3.7/Lib/asyncio/runners.py
asyncio.run(show_disconnect_handling())
