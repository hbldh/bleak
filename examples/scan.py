
import sys
sys.path.insert(1, '../')  # Use local bleak
import logging
import os
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


import asyncio
from bleak import BleakScanner

def detection_callback(*args):
    print("------------------")
    print(args)

async def run():
    scanner = BleakScanner()
    scanner.register_detection_callback(detection_callback)
    await scanner.start()
    await asyncio.sleep(5.0)
    await scanner.stop()
    devices = await scanner.get_discovered_devices()

    for d in devices:
        print(d)

loop = asyncio.get_event_loop()
loop.run_until_complete(run())