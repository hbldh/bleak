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
from bleak.uuids import uuid16_dict, uuid128_dict

logger = logging.getLogger(__name__)


def simple_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    logger.info(f"{device.address} RSSI: {device.rssi}, {advertisement_data}")


async def main(service_uuids):
    if len(service_uuids) > 0 and service_uuids[0] == "all":
        # in Macos Monterey the service_uuids need to be specified.
        # Instead of discovering valid uuids with a different tool
        # you can add `all` as argument and it will add all defined
        # uuid's from bleak/uuids as a starting point.
        logger.info("Adding all known service uuids")
        service_uuids.pop(0)
        for item in uuid16_dict:
            service_uuids.append("{0:04x}".format(item))
        service_uuids.extend(uuid128_dict.keys())
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
