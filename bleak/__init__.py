# -*- coding: utf-8 -*-

"""Top-level package for bleak."""

__author__ = """Henrik Blidh"""
__email__ = "henrik.blidh@gmail.com"

import os
import sys
import logging
import platform
import asyncio

from bleak.__version__ import __version__  # noqa: F401
from bleak.exc import BleakError

_on_rtd = os.environ.get("READTHEDOCS") == "True"

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
if bool(os.environ.get("BLEAK_LOGGING", False)):
    FORMAT = "%(asctime)-15s %(name)-8s %(levelname)s: %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt=FORMAT))
    _logger.addHandler(handler)
    _logger.setLevel(logging.DEBUG)

if _on_rtd:
    pass
elif os.environ.get("P4A_BOOTSTRAP") is not None:
    from bleak.backends.p4android.scanner import (
        BleakScannerP4Android as BleakScanner,
    )  # noqa: F401
    from bleak.backends.p4android.client import (
        BleakClientP4Android as BleakClient,
    )  # noqa: F401
elif platform.system() == "Linux":
    from bleak.backends.bluezdbus.scanner import (
        BleakScannerBlueZDBus as BleakScanner,
    )  # noqa: F401
    from bleak.backends.bluezdbus.client import (
        BleakClientBlueZDBus as BleakClient,
    )  # noqa: F401
elif platform.system() == "Darwin":
    try:
        from CoreBluetooth import CBPeripheral  # noqa: F401
    except Exception as ex:
        raise BleakError("Bleak requires the CoreBluetooth Framework") from ex

    from bleak.backends.corebluetooth.scanner import (
        BleakScannerCoreBluetooth as BleakScanner,
    )  # noqa: F401
    from bleak.backends.corebluetooth.client import (
        BleakClientCoreBluetooth as BleakClient,
    )  # noqa: F401

elif platform.system() == "Windows":
    # Requires Windows 10 Creators update at least, i.e. Window 10.0.16299
    _vtup = platform.win32_ver()[1].split(".")
    if int(_vtup[0]) != 10:
        raise BleakError(
            "Only Windows 10 is supported. Detected was {0}".format(
                platform.win32_ver()
            )
        )

    if (int(_vtup[1]) == 0) and (int(_vtup[2]) < 16299):
        raise BleakError(
            "Requires at least Windows 10 version 0.16299 (Fall Creators Update)."
        )

    from bleak.backends.winrt.scanner import (
        BleakScannerWinRT as BleakScanner,
    )  # noqa: F401
    from bleak.backends.winrt.client import (
        BleakClientWinRT as BleakClient,
    )  # noqa: F401

else:
    raise BleakError(f"Unsupported platform: {platform.system()}")

# for backward compatibility
if not _on_rtd:
    discover = BleakScanner.discover


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
