"""
Detection callback w/ scanner
--------------

Example showing what is returned using the callback upon detection functionality

Updated on 2020-10-11 by bernstern <bernie@allthenticate.net>

"""

import asyncio
from bleak import BleakScanner
from bleak.backends.scanner import AdvertisementData
import logging

logging.basicConfig()


def simple_callback(callback_data: AdvertisementData):
    print(callback_data)


async def run():
    scanner = BleakScanner()
    scanner.register_detection_callback(simple_callback)

    while True:
        await scanner.start()
        await asyncio.sleep(1)
        await scanner.stop()


loop = asyncio.get_event_loop()
loop.run_until_complete(run())
