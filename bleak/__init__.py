# -*- coding: utf-8 -*-

"""Top-level package for bleak."""

__author__ = """Henrik Blidh"""
__email__ = "henrik.blidh@gmail.com"

import os
import sys
import logging
import asyncio

from bleak.__version__ import __version__  # noqa: F401
from bleak.exc import BleakError
from bleak._api import BleakScanner, BleakClient, discover

__all__ = ["BleakError", "BleakScanner", "BleakClient", "discover", "cli"]

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
if bool(os.environ.get("BLEAK_LOGGING", False)):
    FORMAT = "%(asctime)-15s %(name)-8s %(levelname)s: %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt=FORMAT))
    _logger.addHandler(handler)
    _logger.setLevel(logging.DEBUG)

def cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Perform Bluetooth Low Energy device scan"
    )
    parser.add_argument("-i", dest="adapter", default="hci0", help="HCI device")
    parser.add_argument(
        "-t", dest="timeout", type=int, default=5, help="Duration to scan for"
    )
    args = parser.parse_args()

    out = asyncio.run(discover(adapter=args.adapter, timeout=float(args.timeout)))
    for o in out:
        print(str(o))


if __name__ == "__main__":
    cli()
