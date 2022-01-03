"""
Detection callback w/ scanner
--------------

Example showing what is returned using the callback upon detection functionality

Updated on 2020-10-11 by bernstern <bernie@allthenticate.net>

"""

import asyncio
import logging
import platform
import sys

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.uuids import uuid16_dict, uuid128_dict

logger = logging.getLogger(__name__)


def simple_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    logger.info(f"{device.address} RSSI: {device.rssi}, {advertisement_data}")


async def main(service_uuids):
    mac_ver = platform.mac_ver()[0].split(".")
    if mac_ver[0] and int(mac_ver[0]) >= 12 and not service_uuids:
        # In macOS 12 Monterey the service_uuids need to be specified. As a
        # workaround for this example program, we scan for all known UUIDs to
        # increse the chance of at least something showing up. However, in a
        # "real" program, only the device-specific advertised UUID should be
        # used. Devices that don't advertize at least one service UUID cannot
        # currently be detected.
        logger.warning(
            "Scanning using all known service UUIDs to work around a macOS 12 bug. Some devices may not be detected. Please report this to Apple using the Feedback Assistant app and reference <https://github.com/hbldh/bleak/issues/635>."
        )
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
