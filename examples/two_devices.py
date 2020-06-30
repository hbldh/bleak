from bleak import BleakClient, discover, BleakError
import asyncio

temperatureUUID = "45366e80-cf3a-11e1-9ab4-0002a5d5c51b"
ecgUUID = "46366e80-cf3a-11e1-9ab4-0002a5d5c51b"

notify_uuid = "0000{0:x}-0000-1000-8000-00805f9b34fb".format(0xffe1)


def callback(sender, data):
    print(sender, data)

def run(addresses):
    loop = asyncio.get_event_loop()

    tasks = asyncio.gather(
        *(connect_to_device(address, loop) for address in addresses)
    )

    loop.run_until_complete(tasks)

async def connect_to_device(address, loop):
    print("starting", address, "loop")
    async with BleakClient(address, loop=loop, timeout=5.0) as client:

        print("connect to", address)
        try:
            await client.start_notify(notify_uuid, callback)
            await asyncio.sleep(10.0, loop=loop)
            await client.stop_notify(notify_uuid)
        except Exception as e:
            print(e)

    print("disconnect from", address)

if __name__ == "__main__":
    run(["B9EA5233-37EF-4DD6-87A8-2A875E821C46", "F0CBEBD3-299B-4139-A9FC-44618C720157" ])
