import asyncio

from bleak import BleakClient


async def print_services(mac_addr: str, loop: asyncio.AbstractEventLoop):
    async with BleakClient(mac_addr, loop=loop) as client:
        svcs = await client.get_services()
        print("Services:", svcs)


mac_addr = "ff:50:35:82:3b:5a"
loop = asyncio.get_event_loop()
loop.run_until_complete(print_services(mac_addr, loop))
