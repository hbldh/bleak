"""
Services
----------------

An example showing how to pair using Passkey Entry pairing method using pre-shared passkey

Created on 2021-04-20 by Bojan Potočnik <info@bojanpotocnik.com>

"""

import asyncio
import platform
from typing import Union

from bleak import BleakClient


# os.environ["BLEAK_LOGGING"] = "1"


def get_passkey(
    device: str, pin: Union[None, str], passkey: Union[None, int]
) -> Union[bool, int, str, None]:
    if pin:
        print(f"Device {device} is displaying pin '{pin}'")
        return True

    if passkey:
        print(f"Device {device} is displaying passkey '{passkey:06d}'")
        return True

    # Retrieve passkey using custom algorithm, web API or just ask the user like OS pairing
    # wizard would do
    psk = input(
        f"Provide pin (1-16 characters) or passkey (0-999999) for {device}, or nothing to reject "
        f"pairing: "
    )

    # Return None if psk is empty string (pincode 0 is valid pin, but "0" is True)
    return psk or None


async def main(mac_addr: str):
    # Remove this device if it is already paired (from previous runs)
    if await BleakClient.remove_device(mac_addr):
        print(f"Device {mac_addr} was unpaired")

    # Pairing agent shall be registered before initiating the connection
    async with BleakClient(mac_addr, handle_pairing=True) as client:
        print("Pairing...")
        print(await client.pair(callback=get_passkey))
        print("Paired")

        services = await client.get_services()
        print(services)
        for service in services:
            print(service)
            for char in service.characteristics:
                print("\t", char)
                print("\t\tValue: ", await client.read_gatt_char(char))


if platform.system() == "Darwin":
    raise EnvironmentError(
        "Pairing methods other than Just Works are currently implemented only on BlueZ, .NET, and "
        "WinRT backend."
    )

loop = asyncio.get_event_loop()
loop.set_debug(True)
loop.run_until_complete(main("24:71:89:cc:09:05"))
