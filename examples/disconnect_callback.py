"""
Disconnect callback
-------------------

An example showing how the `set_disconnect_callback` can be used on BlueZ backend.

Updated on 2019-09-07 by hbldh <henrik.blidh@gmail.com>

"""

import asyncio

from bleak import BleakClient


async def show_disconnect_handling(mac_addr: str, loop: asyncio.AbstractEventLoop):
    async with BleakClient(mac_addr, loop=loop) as client:
        disconnected_event = asyncio.Event()

        def disconnect_callback(client, future):
            print("Disconnected callback called!")
            loop.call_soon_threadsafe(disconnected_event.set)

        client.set_disconnected_callback(disconnect_callback)
        print("Sleeping until device disconnects according to BlueZ...")
        await disconnected_event.wait()
        print("Connected: {0}".format(await client.is_connected()))
        await asyncio.sleep(
            0.5
        )  # Sleep a bit longer to allow _cleanup to remove all BlueZ notifications nicely...


mac_addr = "24:71:89:cc:09:05"
loop = asyncio.get_event_loop()
loop.run_until_complete(show_disconnect_handling(mac_addr, loop))
