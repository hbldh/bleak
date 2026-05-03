"""
Connected Devices
-----------------

Example showing how to list BLE devices that are already connected
to the OS, with optional service discovery on the existing connection.

"""

import argparse
import asyncio

from bleak import BleakAdapter, BleakClient


class Args(argparse.Namespace):
    service_uuids: list[str] | None
    details: bool


async def main(args: Args) -> None:
    print("Retrieving connected devices...")

    adapter = await BleakAdapter.get()

    if args.service_uuids:
        devices = await adapter.get_connected_devices(args.service_uuids)
    else:
        devices = await adapter.get_connected_devices()

    if not devices:
        print("No connected devices found.")
        return

    print(f"Found {len(devices)} connected device(s):\n")

    for d in devices:
        print(f"  {d.name or '(unnamed)'} [{d.address}]")

    target = devices[0]
    print(f"\nServices on {target.name} [{target.address}]:")

    async with BleakClient(target) as client:
        for service in client.services:
            print(f"\n  [Service] {service.uuid}")

            if not args.details:
                continue

            for char in service.characteristics:
                props = ", ".join(char.properties)
                print(f"    [Char] {char.uuid} ({props})")

                for desc in char.descriptors:
                    print(f"      [Desc] {desc.uuid}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List connected BLE devices")

    parser.add_argument(
        "--service-uuids",
        nargs="*",
        metavar="UUID",
        help="service UUIDs to filter on (defaults to Generic Attribute Profile)",
    )

    parser.add_argument(
        "--details",
        action="store_true",
        help="also print characteristics and descriptors",
    )

    args = parser.parse_args(namespace=Args())

    asyncio.run(main(args))
