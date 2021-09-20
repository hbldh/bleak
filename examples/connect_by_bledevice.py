"""
Connect by BLEDevice
"""

import asyncio
import platform
import sys

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError


ADDRESS = (
    "24:71:89:cc:09:05"
    if platform.system() != "Darwin"
    else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
)
if len(sys.argv) == 2:
    ADDRESS = sys.argv[1]


async def print_services(ble_address: str):
    device = await BleakScanner.find_device_by_address(ble_address, timeout=20.0)
    if not device:
        raise BleakError(f"A device with address {ble_address} could not be found.")
    async with BleakClient(device) as client:
        svcs = await client.get_services()
        print("Services:")
        for service in svcs:
            print(service)


loop = asyncio.get_event_loop()
loop.run_until_complete(print_services(ADDRESS))
