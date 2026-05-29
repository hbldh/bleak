"""
Pair with a BLE device using pairing callbacks.

Run with ``--address <addr>`` or ``--name <name>``. Pairing happens during
connection (``pair=True``), which is the reliable path for devices that only
bond while connecting. Use ``--unpair`` to remove an existing bond first.

Pairing callbacks are only supported on Windows and Linux. Console prompts run
in a worker thread via :func:`asyncio.to_thread` so the event loop is not
blocked.
"""

import argparse
import asyncio
import logging

from bleak import BleakClient, BleakScanner
from bleak.agent import ConfirmPasskey, DisplayPasskey, PairingCallbacks, RequestPasskey
from bleak.exc import BleakDeviceNotFoundError, BleakError


async def confirm_passkey(request: ConfirmPasskey) -> bool:
    answer = await asyncio.to_thread(
        input, f"Does {request.device.name} show {request.passkey:06d}? [y/N] "
    )
    return answer.strip().lower().startswith("y")


async def request_passkey(request: RequestPasskey) -> int | None:
    answer = await asyncio.to_thread(
        input, f"Enter the passkey shown on {request.device.name}: "
    )
    try:
        return int(answer)
    except ValueError:
        return None


async def display_passkey(request: DisplayPasskey) -> None:
    print(f"Enter {request.passkey:06d} on {request.device.name}")


CALLBACKS = PairingCallbacks(
    confirm=confirm_passkey,
    request_passkey=request_passkey,
    display_passkey=display_passkey,
)


async def main(address: str | None, name: str | None, unpair: bool) -> None:
    target = address if address is not None else name

    if unpair and target is not None:
        print("unpairing...")
        try:
            await BleakClient(target).unpair()
            print("unpaired")
        except BleakDeviceNotFoundError:
            print("device was not paired")

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

    print("connecting and pairing...")
    try:
        async with BleakClient(
            device, pairing_callbacks=CALLBACKS, pair=True
        ) as client:
            print(f"connected and paired to {client.address}")
    except BleakError as e:
        print(f"pairing failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("pairing_agent.py")

    device_group = parser.add_mutually_exclusive_group(required=True)
    device_group.add_argument(
        "--name", metavar="<name>", help="the name of the device to connect to"
    )
    device_group.add_argument(
        "--address", metavar="<address>", help="the address of the device to connect to"
    )

    parser.add_argument("--unpair", action="store_true", help="unpair before pairing")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    asyncio.run(main(args.address, args.name, args.unpair))
