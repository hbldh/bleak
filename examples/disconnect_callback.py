"""
Disconnect callback
-------------------

An example showing how the `set_disconnected_callback` can be used on BlueZ backend.

Updated on 2019-09-07 by hbldh <henrik.blidh@gmail.com>

"""

import argparse
import asyncio
import logging
from typing import Optional

from bleak import BleakClient, BleakScanner

logger = logging.getLogger(__name__)


class Args(argparse.Namespace):
    name: Optional[str]
    address: Optional[str]
    macos_use_bdaddr: bool
    debug: bool


async def main(args: Args):
    logger.info("scanning...")

    if args.address:
        device = await BleakScanner.find_device_by_address(
            args.address, cb={"use_bdaddr": args.macos_use_bdaddr}
        )
        if device is None:
            logger.error("could not find device with address '%s'", args.address)
            return
    elif args.name:
        device = await BleakScanner.find_device_by_name(
            args.name, cb={"use_bdaddr": args.macos_use_bdaddr}
        )
        if device is None:
            logger.error("could not find device with name '%s'", args.name)
            return
    else:
        raise ValueError("Either --name or --address must be provided")

    disconnected_event = asyncio.Event()

    def disconnected_callback(client: BleakClient):
        logger.info("Disconnected callback called!")
        disconnected_event.set()

    async with BleakClient(
        device, disconnected_callback=disconnected_callback
    ) as client:
        logger.info("Sleeping until device disconnects...")
        await disconnected_event.wait()
        logger.info("Connected: %r", client.is_connected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    device_group = parser.add_mutually_exclusive_group(required=True)

    device_group.add_argument(
        "--name",
        metavar="<name>",
        help="the name of the bluetooth device to connect to",
    )
    device_group.add_argument(
        "--address",
        metavar="<address>",
        help="the address of the bluetooth device to connect to",
    )

    parser.add_argument(
        "--macos-use-bdaddr",
        action="store_true",
        help="when true use Bluetooth address instead of UUID on macOS",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="sets the log level to debug",
    )

    args = parser.parse_args(namespace=Args())

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    asyncio.run(main(args))
