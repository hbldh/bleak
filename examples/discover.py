"""
Scan/Discovery
--------------

Example showing how to scan for BLE devices.

Updated on 2019-03-25 by hbldh <henrik.blidh@nedomkull.com>

"""

import argparse
import asyncio

from bleak import BleakScanner


class Args(argparse.Namespace):
    macos_use_bdaddr: bool
    services: list[str]


async def main(args: Args):
    print("scanning for 5 seconds, please wait...")

    devices = await BleakScanner.discover(
        return_adv=True,
        service_uuids=args.services,
        cb={"use_bdaddr": args.macos_use_bdaddr},
    )

    for d, a in devices.values():
        print()
        print(d)
        print("-" * len(str(d)))
        print(a)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--services",
        metavar="<uuid>",
        nargs="*",
        help="UUIDs of one or more services to filter for",
    )

    parser.add_argument(
        "--macos-use-bdaddr",
        action="store_true",
        help="when true use Bluetooth address instead of UUID on macOS",
    )

    args = parser.parse_args(namespace=Args())

    asyncio.run(main(args))
