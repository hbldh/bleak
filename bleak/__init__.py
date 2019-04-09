# -*- coding: utf-8 -*-

"""Top-level package for bleak."""

__author__ = """Henrik Blidh"""
__email__ = "henrik.blidh@nedomkull.com"

import re
import os
import sys
import logging
import platform
import subprocess
import asyncio

from bleak.__version__ import __version__  # noqa
from bleak.exc import BleakError

_on_rtd = os.environ.get("READTHEDOCS") == "True"

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
_logger.setLevel(logging.DEBUG)
if bool(os.environ.get("BLEAK_LOGGING", False)):
    FORMAT = "%(asctime)-15s %(name)-8s %(levelname)s: %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt=FORMAT))
    _logger.addHandler(handler)

if platform.system() == "Linux":
    if not _on_rtd:
        # TODO: Check if BlueZ version 5.43 is sufficient.
        p = subprocess.Popen(["bluetoothctl", "--version"], stdout=subprocess.PIPE)
        out, _ = p.communicate()
        s = re.search(b"(\\d+).(\\d+)", out.strip(b"'"))
        if not s:
            raise BleakError("Could not determine BlueZ version: {0}".format(out))

        major, minor = s.groups()
        if not (int(major) == 5 and int(minor) >= 43):
            raise BleakError(
                "Bleak requires BlueZ >= 5.43. Found version {0} installed.".format(out)
            )

    from bleak.backends.bluezdbus.discovery import discover  # noqa
    from bleak.backends.bluezdbus.client import (
        BleakClientBlueZDBus as BleakClient
    )  # noqa
elif platform.system() == "Darwin":
    # TODO: Check if macOS version has Core Bluetooth, raise error otherwise.
    from bleak.backends.corebluetooth import (
        BleakClientCoreBluetooth as BleakClient,
        discover,
    )  # noqa
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

    from bleak.backends.dotnet.discovery import discover  # noqa
    from bleak.backends.dotnet.client import BleakClientDotNet as BleakClient  # noqa


def cli():
    import argparse
    from asyncio.tasks import ensure_future

    loop = asyncio.get_event_loop()

    parser = argparse.ArgumentParser(
        description="Perform Bluetooth Low Energy device scan"
    )
    parser.add_argument("-i", dest="dev", default="hci0", help="HCI device")
    parser.add_argument(
        "-t", dest="timeout", type=int, default=5, help="Duration to scan for"
    )
    args = parser.parse_args()

    out = loop.run_until_complete(
        ensure_future(discover(device=args.dev, timeout=float(args.timeout)))
    )
    for o in out:
        print(str(o))


if __name__ == "__main__":
    cli()
