"""
Bleak Scanner
-------------



Updated on 2020-08-12 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
import platform
import sys

from bleak import BleakScanner


if len(sys.argv) != 2:
    print(f'Usage: {sys.argv[0]} name')
    sys.exit(1)
wanted_name = sys.argv[1].lower()


async def run():
    device = await BleakScanner.find_device_by_filter(lambda d, ad : d.name and d.name.lower() == wanted_name)
    print(device)


loop = asyncio.get_event_loop()
loop.run_until_complete(run())
