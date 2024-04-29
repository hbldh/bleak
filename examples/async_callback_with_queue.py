"""
Async callbacks with a queue and external consumer
--------------------------------------------------

An example showing how async notification callbacks can be used to
send data received through notifications to some external consumer of
that data.

Created on 2021-02-25 by hbldh <henrik.blidh@nedomkull.com>

"""

import argparse
import asyncio
import logging
import time

from bleak import BleakClient, BleakScanner

logger = logging.getLogger(__name__)


class DeviceNotFoundError(Exception):
    pass


async def run_ble_client(args: argparse.Namespace, queue: asyncio.Queue):
    logger.info("starting scan...")

    if args.address:
        device = await BleakScanner.find_device_by_address(
            args.address, cb=dict(use_bdaddr=args.macos_use_bdaddr)
        )
        if device is None:
            logger.error("could not find device with address '%s'", args.address)
            raise DeviceNotFoundError
    else:
        device = await BleakScanner.find_device_by_name(
            args.name, cb=dict(use_bdaddr=args.macos_use_bdaddr)
        )
        if device is None:
            logger.error("could not find device with name '%s'", args.name)
            raise DeviceNotFoundError

    logger.info("connecting to device...")

    async def callback_handler(_, data):
        await queue.put((time.time(), data))

    async with BleakClient(device) as client:
        logger.info("connected")
        await client.start_notify(args.characteristic, callback_handler)
        await asyncio.sleep(10.0)
        await client.stop_notify(args.characteristic)
        # Send an "exit command to the consumer"
        await queue.put((time.time(), None))

    logger.info("disconnected")


async def run_queue_consumer(queue: asyncio.Queue):
    logger.info("Starting queue consumer")

    while True:
        # Use await asyncio.wait_for(queue.get(), timeout=1.0) if you want a timeout for getting data.
        epoch, data = await queue.get()
        if data is None:
            logger.info(
                "Got message from client about disconnection. Exiting consumer loop..."
            )
            break
        else:
            logger.info("Received callback data via async queue at %s: %r", epoch, data)


async def main(args: argparse.Namespace):
    queue = asyncio.Queue()
    client_task = run_ble_client(args, queue)
    consumer_task = run_queue_consumer(queue)

    try:
        await asyncio.gather(client_task, consumer_task)
    except DeviceNotFoundError:
        pass

    logger.info("Main method done.")


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
        "characteristic",
        metavar="<notify uuid>",
        help="UUID of a characteristic that supports notifications",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="sets the logging level to debug",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    asyncio.run(main(args))
