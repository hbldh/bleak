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
from bleak._api import (
    BleakScanner,
    _BleakScannerImplementation,
    BleakClient,
    _BleakClientImplementation,
    BLEDevice,
    _BLEDeviceImplementation,
    AdvertisementData,
    AdvertisementDataCallback,
    AdvertisementDataFilter,
    BleakGATTServiceCollection,
    BleakGATTService,
    _BleakGATTServiceImplementation,
    BleakGATTCharacteristic,
    _BleakGATTCharacteristicImplementation,
    BleakGATTDescriptor,
    _BleakGATTDescriptorImplementation,
)

__all__ = [
    "BleakError",
    "BleakScanner",
    "BleakClient",
    "BLEDevice",
    "AdvertisementData",
    "AdvertisementDataCallback",
    "AdvertisementDataFilter",
    "BleakGATTServiceCollection",
    "BleakGATTService",
    "BleakGATTCharacteristic",
    "BleakGATTDescriptor",
    "discover",
]

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())
if bool(os.environ.get("BLEAK_LOGGING", False)):
    FORMAT = "%(asctime)-15s %(name)-8s %(levelname)s: %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(fmt=FORMAT))
    _logger.addHandler(handler)
    _logger.setLevel(logging.DEBUG)

