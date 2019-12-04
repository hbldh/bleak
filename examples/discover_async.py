import asyncio

from bleak.backends.bluezdbus.discovery import discover_async

def device_found(bleak_dev):
    print("Address: ", bleak_dev.address)
    print("Name: ", bleak_dev.name)
    print("Details: ", bleak_dev.details)
    print("Metadata: ", bleak_dev.metadata)
    print("RSSI: ", bleak_dev.rssi)


loop = asyncio.get_event_loop()

disco = loop.run_until_complete(discover_async(device_found, loop))

try:
    loop.run_forever()
except KeyboardInterrupt:
    loop.run_until_complete(disco.stop_discovery())
    print("Goodbye")
