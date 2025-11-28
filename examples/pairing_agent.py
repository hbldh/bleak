import argparse
import asyncio

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from bleak import BaseBleakAgentCallbacks, BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import (
    BleakDeviceNotFoundError,
    BleakPairingCancelledError,
    BleakPairingFailedError,
)


class AgentCallbacks(BaseBleakAgentCallbacks):
    def __init__(self) -> None:
        self.session: PromptSession[str] = PromptSession()

    async def request_passkey(self, device: BLEDevice) -> str:
        print(f"{device.name} wants to pair.")
        with patch_stdout():
            response = await self.session.prompt_async("enter passkey: ")

        return response

    async def confirm_passkey(self, device: BLEDevice, passkey: str) -> bool:
        print(f"{device.name} wants to pair.")
        with patch_stdout():
            response = await self.session.prompt_async(f"does {passkey} match (y/n)?")

        return response.lower().startswith("y")


async def main(address: str | None, name: str | None, unpair: bool, auto: bool) -> None:
    if unpair:
        print("unpairing...")
        try:
            if address:
                await BleakClient(address).unpair()
            elif name:
                await BleakClient(name).unpair()
            print("unpaired")
        except BleakDeviceNotFoundError:
            print("device was not paired")

    print("scanning...")

    if address:
        device = await BleakScanner.find_device_by_address(address)
        if device is None:
            print(f"could not find device with address '{address}'")
            return
    elif name:
        device = await BleakScanner.find_device_by_name(name)
        if device is None:
            print(f"could not find device with name '{name}'")
            return
    else:
        raise ValueError("Either --name or --address must be provided")

    callbacks = AgentCallbacks()
    if auto:
        print("connecting and pairing...")

        async with BleakClient(
            device, pair=True, pairing_callbacks=callbacks
        ) as client:
            print(f"connection and pairing to {client.address} successful")

    else:
        print("connecting...")

        async with BleakClient(device, pairing_callbacks=callbacks) as client:
            try:
                print("pairing...")
                await client.pair()
                print("pairing successful")
            except BleakPairingCancelledError:
                print("paring was canceled")
            except BleakPairingFailedError:
                print("pairing failed (bad pin?)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("pairing_agent.py")

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
        "--unpair", action="store_true", help="unpair first before pairing"
    )
    parser.add_argument(
        "--auto", action="store_true", help="automatically pair during connect"
    )
    args = parser.parse_args()

    asyncio.run(main(args.address, args.name, args.unpair, args.auto))
