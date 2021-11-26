"""
Bleak Scanner, find by name
---------------------------

Find a peripheral by advertised name. Calle by

``python scanner_byname.py "Name of my Peripheral"``

Updated on 2020-08-12 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
import sys

from bleak import BleakScanner


async def main(wanted_name):
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and d.name.lower() == wanted_name.lower()
    )
    print(device)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} name")
        sys.exit(1)

    asyncio.run(main(sys.argv[1]))
