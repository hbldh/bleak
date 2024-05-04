"""
Scan/Discovery Async Iterator
--------------

Example showing how to scan for BLE devices using async iterator instead of callback function

Created on 2023-07-07 by bojanpotocnik <info@bojanpotocnik.com>

"""

import asyncio

from bleak import BleakScanner


async def main():
    async with BleakScanner() as scanner:
        print("Scanning...")

        n = 5
        print(f"\n{n} advertisement packets:")
        async for bd, ad in scanner.advertisement_data():
            print(f" {n}. {bd!r} with {ad!r}")
            n -= 1
            if n == 0:
                break

        n = 10
        print(f"\nFind device with name longer than {n} characters...")
        async for bd, ad in scanner.advertisement_data():
            found = len(bd.name or "") > n or len(ad.local_name or "") > n
            print(f" Found{' it' if found else ''} {bd!r} with {ad!r}")
            if found:
                break


if __name__ == "__main__":
    asyncio.run(main())
