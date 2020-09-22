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
        print("Connected: {0}".format(await client.is_connected()))
        await asyncio.sleep(
            0.5
        )  # Sleep a bit longer to allow _cleanup to remove all BlueZ notifications nicely...


loop = asyncio.get_event_loop()
loop.run_until_complete(show_disconnect_handling())
