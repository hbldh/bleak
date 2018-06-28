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

from System import Array
from Windows.Devices import Enumeration

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


async def discover(timeout: float=5.0, loop: AbstractEventLoop=None, **kwargs) -> List[BLEDevice]:
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

    def _format_device_info(d):
        try:
            return "{0}: {1}".format(
                d.Id.split('-')[-1],
                d.Name if d.Name else 'Unknown'
            )
        except Exception:
            return d.Id

    def DeviceWatcher_Added(sender, dinfo):
        if sender == watcher:

            logger.debug("Added {0}.".format(_format_device_info(dinfo)))
            if dinfo.Id not in devices:
                devices[dinfo.Id] = dinfo

    def DeviceWatcher_Updated(sender, dinfo_update):
        if sender == watcher:
            if dinfo_update.Id in devices:
                logger.debug("Updated {0}.".format(
                    _format_device_info(devices[dinfo_update.Id])))
                devices[dinfo_update.Id].Update(dinfo_update)

    def DeviceWatcher_Removed(sender, dinfo_update):
        if sender == watcher:
            logger.debug("Removed {0}.".format(
                _format_device_info(devices[dinfo_update.Id])))
            if dinfo_update.Id in devices:
                devices.pop(dinfo_update.Id)

    def DeviceWatcher_EnumCompleted(sender, obj):
        if sender == watcher:
            logger.debug("{0} devices found. Enumeration completed. Watching for updates...".format(len(devices)))

    def DeviceWatcher_Stopped(sender, obj):
        if sender == watcher:
            logger.debug("{0} devices found. Watcher status: {1}.".format(
                len(devices), watcher.Status))

    watcher.Added += DeviceWatcher_Added
    watcher.Updated += DeviceWatcher_Updated
    watcher.Removed += DeviceWatcher_Removed
    watcher.EnumerationCompleted += DeviceWatcher_EnumCompleted
    watcher.Stopped += DeviceWatcher_Stopped

    # Watcher works outside of the Python process.
    watcher.Start()
    await asyncio.sleep(timeout, loop=loop)
    watcher.Stop()

    try:
        watcher.Added -= DeviceWatcher_Added
        watcher.Updated -= DeviceWatcher_Updated
        watcher.Removed -= DeviceWatcher_Removed
        watcher.EnumerationCompleted -= DeviceWatcher_EnumCompleted
        watcher.Stopped -= DeviceWatcher_Stopped
    except Exception as e:
        logger.debug("Could not remove event handlers: {0}...".format(e))

    found = []
    for d in devices.values():
        properties = {p.Key: p.Value for p in d.Properties}
        found.append(
            BLEDevice(properties["System.Devices.Aep.DeviceAddress"], d.Name, d)
        )

    return found
