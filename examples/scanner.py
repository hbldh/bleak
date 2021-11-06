"""
Bleak Scanner
-------------

Updated on 2020-08-12 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
import platform
import sys

from bleak import BleakScanner


ADDRESS = (
    "24:71:89:cc:09:05"  # <--- Change to your device's address here if you are using Windows or Linux
    if platform.system() != "Darwin"
    else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"  # <--- Change to your device's address here if you are using macOS
)


async def main(address):
    device = await BleakScanner.find_device_by_address(address)
    print(device)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) == 2 else ADDRESS))
