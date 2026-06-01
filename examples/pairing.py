"""
Pair with a BLE device using pairing callbacks.

Run with ``--address <addr>`` or ``--name <name>``. By default pairing happens
during connection (``pair=True``), which is the reliable path for devices that
only bond while connecting. Pass ``--explicit`` to instead connect first and
then pair with an explicit :meth:`~bleak.BleakClient.pair` call. Use
``--unpair`` to remove an existing bond before pairing.

Pairing callbacks are only supported on Windows and Linux. Console prompts run
in a worker thread via :func:`asyncio.to_thread` so the event loop is not
blocked.
"""

import argparse
import asyncio
import logging

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakDeviceNotFoundError, BleakError
from bleak.pairing import (
    MAX_PASSKEY,
    SupportsConfirm,
    SupportsDisplayPasskey,
    SupportsRequestPasskey,
)


class ConsoleCallbacks(SupportsConfirm, SupportsRequestPasskey, SupportsDisplayPasskey):
    """Answer every pairing ceremony from the console."""

    async def confirm(self, device: BLEDevice, passkey: int) -> bool:
        answer = await asyncio.to_thread(
            input, f"Does {device.name} show {passkey:06d}? [y/N] "
        )
        return answer.strip().lower().startswith("y")

    async def request_passkey(self, device: BLEDevice) -> int | None:
        answer = await asyncio.to_thread(
            input, f"Enter the passkey shown on {device.name}: "
        )
        try:
            passkey = int(answer)
        except ValueError:
            return None
        return passkey if 0 <= passkey <= MAX_PASSKEY else None

    async def display_passkey(self, device: BLEDevice, passkey: int) -> None:
        print(f"Enter {passkey:06d} on {device.name}")


CALLBACKS = ConsoleCallbacks()


async def main(
    address: str | None, name: str | None, unpair: bool, explicit: bool
) -> None:
    print("scanning...")
    if address is not None:
        device = await BleakScanner.find_device_by_address(address)
    elif name is not None:
        device = await BleakScanner.find_device_by_name(name)
    else:
        raise ValueError("either --name or --address must be provided")

    if device is None:
        print("could not find device")
        return

    if unpair:
        print("unpairing...")
        try:
            await BleakClient(device).unpair()
            print("unpaired")
        except BleakDeviceNotFoundError:
            print("device was not paired")

    try:
        if explicit:
            async with BleakClient(device, pairing_callbacks=CALLBACKS) as client:
                print(f"connected to {client.address}; pairing...")
                await client.pair()
                print("paired")
        else:
            async with BleakClient(
                device, pairing_callbacks=CALLBACKS, pair=True
            ) as client:
                print(f"connected and paired to {client.address}")
    except BleakError as e:
        print(f"failed to connect or pair: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("pairing.py")

    device_group = parser.add_mutually_exclusive_group(required=True)
    device_group.add_argument(
        "--name", metavar="<name>", help="the name of the device to connect to"
    )
    device_group.add_argument(
        "--address", metavar="<address>", help="the address of the device to connect to"
    )

    parser.add_argument(
        "--explicit",
        action="store_true",
        help="connect first, then pair with an explicit pair() call",
    )
    parser.add_argument("--unpair", action="store_true", help="unpair before pairing")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    asyncio.run(main(args.address, args.name, args.unpair, args.explicit))
