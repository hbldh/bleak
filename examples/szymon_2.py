import logging
import asyncio
import uuid
from functools import partial
from bleak import BleakClient
from queue import Queue
import time


async def run(address_1, address_2, loop, debug=False):
    log = logging.getLogger(__name__)
    if debug:
        import sys

        loop.set_debug(True)
        log.setLevel(logging.DEBUG)
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.DEBUG)
        log.addHandler(h)

    q = Queue()

    def callback(which_client, sender, data):
        print(f"{which_client} - {sender}: {data}")
        q.put((time.time(), which_client, sender, data))

    async with BleakClient(address_1, loop=loop) as client_1, BleakClient(address_2, loop=loop) as client_2:
        tasks = [
            asyncio.create_task(client_1.is_connected()),
            asyncio.create_task(client_2.is_connected()),
        ]
        done, pending = await asyncio.wait(tasks)
        for task in done:
            log.info("Connected: {0}".format(task.result()))
        rw_charac = uuid.UUID("46366E80-CF3A-11E1-9AB4-0002A5D5C51B")

        await client_1.start_notify(
            rw_charac, partial(callback, which_client=str(client_1.address))
        )
        await client_2.start_notify(
            rw_charac, partial(callback, which_client=str(client_2.address))
        )
        await asyncio.sleep(10.0, loop=loop)
        await client_1.stop_notify(rw_charac)
        await client_2.stop_notify(rw_charac)

    while not q.empty():
        v = q.get()
        print(v)


if __name__ == "__main__":
    address_1 = "84:DD:20:E6:A8:FA"
    address_2 = "24:71:89:cc:09:05"
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(address_1, address_2, loop, True))
