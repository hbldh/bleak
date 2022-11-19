"""
Detection callback w/ scanner
--------------

Example showing what is returned using the callback upon detection functionality

Updated on 2020-10-11 by bernstern <bernie@allthenticate.net>

"""

import argparse
import asyncio
import logging

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

logger = logging.getLogger(__name__)


def simple_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    logger.info("%s: %r", device.address, advertisement_data)


async def main(args: argparse.Namespace):
    scanner = BleakScanner(
        simple_callback, args.services, cb=dict(use_bdaddr=args.macos_use_bdaddr)
    )

    while True:
        logger.info("(re)starting scanner")
        await scanner.start()
        await asyncio.sleep(5.0)
        await scanner.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--macos-use-bdaddr",
        action="store_true",
        help="when true use Bluetooth address instead of UUID on macOS",
    )

    parser.add_argument(
        "--services",
        metavar="<uuid>",
        nargs="*",
        help="UUIDs of one or more services to filter for",
    )

    args = parser.parse_args()

    asyncio.run(main(args))
