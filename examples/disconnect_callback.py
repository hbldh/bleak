"""
Disconnect callback
-------------------

An example showing how the `set_disconnected_callback` can be used on BlueZ backend.

Updated on 2019-09-07 by hbldh <henrik.blidh@gmail.com>

"""

import asyncio
import sys

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


if sys.version_info >= (3, 7):
    asyncio.run(show_disconnect_handling())
else:
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(show_disconnect_handling())
    finally:
        try:
            tasks = asyncio.all_tasks(loop)
            if tasks:
                for t in tasks:
                    t.cancel()
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            asyncio.set_event_loop(None)
            loop.close()
