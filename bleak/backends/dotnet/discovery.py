# -*- coding: utf-8 -*-
"""
Perform Bluetooth LE Scan.

Created on 2017-12-05 by hbldh <henrik.blidh@nedomkull.com>

"""
import pathlib
import logging
import asyncio

from bleak.backends.device import BLEDevice

from System import Array
from Windows.Devices import Enumeration

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


async def discover(timeout=5.0, loop=None, **kwargs):
    """Perform a Bluetooth LE Scan.

    Args:
        timeout (float): Time to scan for.
        loop (Event Loop): The event loop to use.

    Keyword Args:
        string_output (bool): If set to false, ``discover`` returns .NET
            device objects instead.

    Returns:
        List of strings or  objects found.

    """
    loop = loop if loop else asyncio.get_event_loop()

    requested_properties = Array[str](
        [
            "System.Devices.Aep.DeviceAddress",
            "System.Devices.Aep.IsConnected",
            "System.Devices.Aep.Bluetooth.Le.IsConnectable",
        ]
    )
    aqs_all_bluetooth_le_devices = '(System.Devices.Aep.ProtocolId:="' \
                                   '{bb7bb05e-5972-42b5-94fc-76eaa7084d49}")'
    watcher = Enumeration.DeviceInformation.CreateWatcher(
        aqs_all_bluetooth_le_devices,
        requested_properties,
        Enumeration.DeviceInformationKind.AssociationEndpoint,
    )

    devices = {}

    def DeviceWatcher_Added(sender, dinfo):
        if sender == watcher:
            logger.debug("Added {0}.".format(dinfo.Id))
            if dinfo.Id not in devices:
                devices[dinfo.Id] = dinfo

    def DeviceWatcher_Updated(sender, dinfo_update):
        if sender == watcher:
            logger.debug("Updated {0}.".format(dinfo_update.Id))
            if dinfo_update.Id in devices:
                devices[dinfo_update.Id].Update(dinfo_update)

    def DeviceWatcher_Removed(sender, dinfo_update):
        if sender == watcher:
            logger.debug("Removed {0}.".format(dinfo_update.Id))
            if dinfo_update.Id in devices:
                devices.pop(dinfo_update.Id)

    watcher.Added += DeviceWatcher_Added
    watcher.Updated += DeviceWatcher_Updated
    watcher.Removed += DeviceWatcher_Removed

    # Watcher works outside of the Python process.
    watcher.Start()
    await asyncio.sleep(timeout, loop=loop)
    watcher.Stop()

    try:
        watcher.Added -= DeviceWatcher_Added
        watcher.Updated -= DeviceWatcher_Updated
        watcher.Removed -= DeviceWatcher_Removed
    except Exception:
        logger.debug("Could not remove event handlers...")

    found = []
    for d in devices.values():
        properties = {p.Key: p.Value for p in d.Properties}
        found.append(
            BLEDevice(properties["System.Devices.Aep.DeviceAddress"], d.Name, d)
        )

    return found
