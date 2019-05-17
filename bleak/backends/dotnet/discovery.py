# -*- coding: utf-8 -*-
"""
Perform Bluetooth LE Scan.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>

"""
import pathlib
import logging
import asyncio
from typing import List
from asyncio.events import AbstractEventLoop

from bleak.backends.device import BLEDevice

# Import of Bleak CLR->UWP Bridge. It is not needed here, but it enables loading of Windows.Devices
from BleakBridge import Bridge

from System import Array, Byte
from Windows.Devices.Bluetooth.Advertisement import BluetoothLEAdvertisementWatcher
from Windows.Storage.Streams import DataReader, IBuffer

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


async def discover(
    timeout: float = 5.0, loop: AbstractEventLoop = None, **kwargs
) -> List[BLEDevice]:
    """Perform a Bluetooth LE Scan.

    Args:
        timeout (float): Time to scan for.
        loop (Event Loop): The event loop to use.

    Keyword Args:
        string_output (bool): If set to false, ``discover`` returns .NET
            device objects instead.

    Returns:
        List of strings or objects found.

    """
    loop = loop if loop else asyncio.get_event_loop()

    watcher = BluetoothLEAdvertisementWatcher()

    devices = {}

    def _format_bdaddr(a):
        return ":".join("{:02X}".format(x) for x in a.to_bytes(6, byteorder="big"))

    def _format_event_args(e):
        try:
            return "{0}: {1}".format(
                _format_bdaddr(e.BluetoothAddress),
                e.Advertisement.LocalName or "Unknown",
            )
        except Exception:
            return e.BluetoothAddress

    def AdvertisementWatcher_Received(sender, e):
        if sender == watcher:
            logger.debug("Received {0}.".format(_format_event_args(e)))
            if e.BluetoothAddress not in devices:
                devices[e.BluetoothAddress] = e

    def AdvertisementWatcher_Stopped(sender, e):
        if sender == watcher:
            logger.debug(
                "{0} devices found. Watcher status: {1}.".format(
                    len(devices), watcher.Status
                )
            )

    watcher.Received += AdvertisementWatcher_Received
    watcher.Stopped += AdvertisementWatcher_Stopped

    # Watcher works outside of the Python process.
    watcher.Start()
    await asyncio.sleep(timeout, loop=loop)
    watcher.Stop()

    try:
        watcher.Received -= AdvertisementWatcher_Received
        watcher.Stopped -= AdvertisementWatcher_Stopped
    except Exception as e:
        logger.debug("Could not remove event handlers: {0}...".format(e))

    found = []
    for d in devices.values():
        bdaddr = _format_bdaddr(d.BluetoothAddress)
        uuids = []
        for u in d.Advertisement.ServiceUuids:
            uuids.append(u.ToString())
        data = {}
        for m in d.Advertisement.ManufacturerData:
            md = IBuffer(m.Data)
            b = Array.CreateInstance(Byte, md.Length)
            reader = DataReader.FromBuffer(md)
            reader.ReadBytes(b)
            data[m.CompanyId] = bytes(b)
        found.append(BLEDevice(bdaddr, d.Advertisement.LocalName, d, uuids=uuids, manufacturer_data=data))

    return found
