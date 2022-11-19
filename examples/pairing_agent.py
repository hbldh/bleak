import argparse
import asyncio
import sys

from bleak import BleakScanner, BleakClient, BaseBleakAgentCallbacks
from bleak.backends.device import BLEDevice
from bleak.exc import BleakPairingCancelledError, BleakPairingFailedError


class AgentCallbacks(BaseBleakAgentCallbacks):
    def __init__(self) -> None:
        super().__init__()
        self._reader = asyncio.StreamReader()

    async def __aenter__(self):
        loop = asyncio.get_running_loop()
        protocol = asyncio.StreamReaderProtocol(self._reader)
        self._input_transport, _ = await loop.connect_read_pipe(
            lambda: protocol, sys.stdin
        )
        return self

    async def __aexit__(self, *args):
        self._input_transport.close()

    async def _input(self, msg: str) -> str:
        """
        Async version of the builtin input function.
        """
        print(msg, end=" ", flush=True)
        return (await self._reader.readline()).decode().strip()

    async def confirm(self, device: BLEDevice) -> bool:
        print(f"{device.name} wants to pair.")
        response = await self._input("confirm (y/n)?")

        return response.lower().startswith("y")

    async def confirm_pin(self, device: BLEDevice, pin: str) -> bool:
        print(f"{device.name} wants to pair.")
        response = await self._input(f"does {pin} match (y/n)?")

        return response.lower().startswith("y")

    async def display_pin(self, device: BLEDevice, pin: str) -> None:
        print(f"{device.name} wants to pair.")
        print(f"enter this pin on the device: {pin}")
        # wait for cancellation
        await asyncio.Event().wait()

    async def request_pin(self, device: BLEDevice) -> str:
        print(f"{device.name} wants to pair.")
        response = await self._input("enter pin:")

        return response


async def main(addr: str, unpair: bool) -> None:
    if unpair:
        print("unpairing...")
        await BleakClient(addr).unpair()

    print("scanning...")

    device = await BleakScanner.find_device_by_address(addr)

    if device is None:
        print("device was not found")
        return

    async with BleakClient(device) as client, AgentCallbacks() as callbacks:
        try:
            await client.pair(callbacks)
        except BleakPairingCancelledError:
            print("paring was canceled")
        except BleakPairingFailedError:
            print("pairing failed (bad pin?)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("pairing_agent.py")
    parser.add_argument("address", help="the Bluetooth address (or UUID on macOS)")
    parser.add_argument(
        "--unpair", action="store_true", help="unpair first before pairing"
    )
    args = parser.parse_args()

    asyncio.run(main(args.address, args.unpair))
