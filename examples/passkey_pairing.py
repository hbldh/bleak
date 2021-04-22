"""
Services
----------------

An example showing how to pair using Passkey Entry pairing method using pre-shared passkey

Created on 2021-04-20 by Bojan Potočnik <info@bojanpotocnik.com>

"""

import asyncio
import os
import platform

os.environ["BLEAK_LOGGING"] = "1"

from bleak import BleakClient


async def main(mac_addr: str):
    # Remove this device if it is already paired (from previous runs)
    if await BleakClient.remove_device(mac_addr):
        print(f"Device {mac_addr} was unpaired")

    # Pairing agent shall be registered before initiating the connection
    async with BleakClient(mac_addr, handle_pairing=True) as client:
        if hasattr(client, "pairingAgent"):
            client.pairingAgent.passkey = 123456
        # else Passkey Entry pairing method is not supported

        print("Pairing...")
        print(await client.pair())
        print("Paired")

        services = await client.get_services()
        print(services)
        for service in services:
            print(service)
            for char in service.characteristics:
                print("\t", char)
                print("\t\tValue: ", await client.read_gatt_char(char))


if platform.system() != "Linux":
    raise EnvironmentError(
        "Pairing methods other than Just Works are currently implemented only on BlueZ backend"
    )

loop = asyncio.get_event_loop()
loop.set_debug(True)
loop.run_until_complete(main("24:71:89:cc:09:05"))
