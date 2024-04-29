"""
Example showing how to use BleakClient.mtu_size
"""

import asyncio

from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData, BLEDevice

# replace with real characteristic UUID
CHAR_UUID = "00000000-0000-0000-0000-000000000000"


async def main():
    queue = asyncio.Queue()

    def callback(device: BLEDevice, adv: AdvertisementData) -> None:
        # can use advertising data to filter here
        queue.put_nowait(device)

    async with BleakScanner(callback):
        # get the first matching device
        device = await queue.get()

    async with BleakClient(device) as client:
        # BlueZ doesn't have a proper way to get the MTU, so we have this hack.
        # If this doesn't work for you, you can set the client._mtu_size attribute
        # to override the value instead.
        if client._backend.__class__.__name__ == "BleakClientBlueZDBus":
            await client._backend._acquire_mtu()

        print("MTU:", client.mtu_size)

        # Write without response is limited to MTU - 3 bytes

        data = bytes(1000)  # replace with real data
        chunk_size = client.mtu_size - 3
        for chunk in (
            data[i : i + chunk_size] for i in range(0, len(data), chunk_size)
        ):
            await client.write_gatt_char(CHAR_UUID, chunk, response=False)


if __name__ == "__main__":
    asyncio.run(main())
