"""
Connect by BLEDevice
"""

import asyncio
import platform

from bleak import BleakClient, BleakScanner


async def print_services(mac_addr: str):
    device = await BleakScanner.find_device_by_address(mac_addr)
    async with BleakClient(device) as client:
        svcs = await client.get_services()
        print("Services:", svcs)


mac_addr = (
    "24:71:89:cc:09:05"
    if platform.system() != "Darwin"
    else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
)
loop = asyncio.get_event_loop()
loop.run_until_complete(print_services(mac_addr))
