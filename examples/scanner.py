"""
Bleak Scanner
-------------



Updated on 2020-08-12 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
import platform
import sys

from bleak import BleakScanner


address = (
    "24:71:89:cc:09:05"  # <--- Change to your device's address here if you are using Windows or Linux
    if platform.system() != "Darwin"
    else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"  # <--- Change to your device's address here if you are using macOS
)
if len(sys.argv) == 2:
    address = sys.argv[1]


async def run():
    device = await BleakScanner.find_device_by_address(address)
    print(device)


loop = asyncio.get_event_loop()
loop.run_until_complete(run())
