"""
Detection callback w/ scanner
--------------

Example showing what is returned using the callback upon detection functionality

Updated on 2020-10-11 by bernstern <bernie@allthenticate.net>

"""

import asyncio
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import logging

logging.basicConfig()


def simple_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    print(device.address, "RSSI:", device.rssi, advertisement_data)


async def main():
    scanner = BleakScanner()
    scanner.register_detection_callback(simple_callback)

    while True:
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()


if __name__ == "__main__":
    asyncio.run(main())
