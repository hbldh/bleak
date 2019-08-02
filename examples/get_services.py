"""
Services
----------------

An example showing how to fetch all services and print them.

Updated on 2019-03-25 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
import platform

from bleak import BleakClient


async def print_services(mac_addr: str, loop: asyncio.AbstractEventLoop):
    async with BleakClient(mac_addr, loop=loop) as client:
        svcs = await client.get_services()
        print("Services:", svcs)


mac_addr = (
    "24:71:89:cc:09:05"
    if platform.system() != "Darwin"
    else "243E23AE-4A99-406C-B317-18F1BD7B4CBE"
)
loop = asyncio.get_event_loop()
loop.run_until_complete(print_services(mac_addr, loop))
