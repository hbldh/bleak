"""
Detection callback w/ scanner
--------------

Example showing what is returned using the callback upon detection functionality

Updated on 2020-10-11 by bernstern <bernie@allthenticate.net>

"""

import asyncio
import logging
import sys

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

logger = logging.getLogger(__name__)


def simple_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    logger.info(f"{device.address} RSSI: {device.rssi}, {advertisement_data}")


async def main(service_uuids):
    scanner = BleakScanner(service_uuids=service_uuids)
    scanner.register_detection_callback(simple_callback)

    while True:
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )
    service_uuids = sys.argv[1:]
    asyncio.run(main(service_uuids))
