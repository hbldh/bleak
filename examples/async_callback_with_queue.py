"""
Async callbacks with a queue and external consumer
--------------------------------------------------

An example showing how async notification callbacks can be used to
send data received through notifications to some external consumer of
that data.

Created on 2021-02-25 by hbldh <henrik.blidh@nedomkull.com>

"""
import sys
import time
import platform
import asyncio
import logging

from bleak import BleakClient

logger = logging.getLogger(__name__)

ADDRESS = (
    "24:71:89:cc:09:05"
    if platform.system() != "Darwin"
    else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
)
CHARACTERISTIC_UUID = f"0000{0xFFE1:x}-0000-1000-8000-00805f9b34fb"


async def run_ble_client(address: str, char_uuid: str, queue: asyncio.Queue):
    async def callback_handler(sender, data):
        await queue.put((time.time(), data))

    async with BleakClient(address) as client:
        logger.info(f"Connected: {client.is_connected}")
        await client.start_notify(char_uuid, callback_handler)
        await asyncio.sleep(10.0)
        await client.stop_notify(char_uuid)
        # Send an "exit command to the consumer"
        await queue.put((time.time(), None))


async def run_queue_consumer(queue: asyncio.Queue):
    while True:
        # Use await asyncio.wait_for(queue.get(), timeout=1.0) if you want a timeout for getting data.
        epoch, data = await queue.get()
        if data is None:
            logger.info(
                "Got message from client about disconnection. Exiting consumer loop..."
            )
            break
        else:
            logger.info(f"Received callback data via async queue at {epoch}: {data}")


async def main(address: str, char_uuid: str):
    queue = asyncio.Queue()
    client_task = run_ble_client(address, char_uuid, queue)
    consumer_task = run_queue_consumer(queue)
    await asyncio.gather(client_task, consumer_task)
    logger.info("Main method done.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(
        main(
            sys.argv[1] if len(sys.argv) > 1 else ADDRESS,
            sys.argv[2] if len(sys.argv) > 2 else CHARACTERISTIC_UUID,
        )
    )
