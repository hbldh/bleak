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
from Windows.Devices import Enumeration
from Windows.Devices.Bluetooth.Advertisement import (
    BluetoothLEAdvertisementWatcher,
    BluetoothLEScanningMode,
    BluetoothLEAdvertisementType,
)
from Windows.Storage.Streams import DataReader, IBuffer

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


async def discover(
    timeout: float = 5.0, loop: AbstractEventLoop = None, **kwargs
) -> List[BLEDevice]:
    """Perform a Bluetooth LE Scan using Windows.Devices.Bluetooth.Advertisement

    Args:
        timeout (float): Time to scan for.
        loop (Event Loop): The event loop to use.

    Keyword Args:
        SignalStrengthFilter (Windows.Devices.Bluetooth.BluetoothSignalStrengthFilter): A
          BluetoothSignalStrengthFilter object used for configuration of Bluetooth
          LE advertisement filtering that uses signal strength-based filtering.
        AdvertisementFilter (Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementFilter): A
          BluetoothLEAdvertisementFilter object used for configuration of Bluetooth LE
          advertisement filtering that uses payload section-based filtering.
        string_output (bool): If set to false, ``discover`` returns .NET
            device objects instead.

    Returns:
        List of strings or objects found.

    """
    signal_strength_filter = kwargs.get("SignalStrengthFilter", None)
    advertisement_filter = kwargs.get("AdvertisementFilter", None)

    loop = loop if loop else asyncio.get_event_loop()

    watcher = BluetoothLEAdvertisementWatcher()

    devices = {}
    scan_responses = {}

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
            if e.AdvertisementType == BluetoothLEAdvertisementType.ScanResponse:
                if e.BluetoothAddress not in scan_responses:
                    scan_responses[e.BluetoothAddress] = e
            else:
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

    watcher.ScanningMode = BluetoothLEScanningMode.Active

    if signal_strength_filter is not None:
        watcher.SignalStrengthFilter = signal_strength_filter
    if advertisement_filter is not None:
        watcher.AdvertisementFilter = advertisement_filter

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
    for d in list(devices.values()):
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
        local_name = d.Advertisement.LocalName
        if not local_name and d.BluetoothAddress in scan_responses:
            local_name = scan_responses[d.BluetoothAddress].Advertisement.LocalName
        found.append(
            BLEDevice(bdaddr, local_name, d, uuids=uuids, manufacturer_data=data,)
        )

    return found


async def discover_by_enumeration(
    timeout: float = 5.0, loop: AbstractEventLoop = None, **kwargs
) -> List[BLEDevice]:
    """Perform a Bluetooth LE Scan using Windows.Devices.Enumeration

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
            "System.ItemNameDisplay",
            "System.Devices.Aep.Manufacturer",
            "System.Devices.Manufacturer",
            "System.Devices.Aep.ModelName",
            "System.Devices.ModelName",
            "System.Devices.Aep.SignalStrength",
        ]
    )
    aqs_all_bluetooth_le_devices = (
        '(System.Devices.Aep.ProtocolId:="' '{bb7bb05e-5972-42b5-94fc-76eaa7084d49}")'
    )
    watcher = Enumeration.DeviceInformation.CreateWatcher(
        aqs_all_bluetooth_le_devices,
        requested_properties,
        Enumeration.DeviceInformationKind.AssociationEndpoint,
    )

    devices = {}

    def _format_device_info(d):
        try:
            return "{0}: {1}".format(
                d.Id.split("-")[-1], d.Name if d.Name else "Unknown"
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
                logger.debug(
                    "Updated {0}.".format(_format_device_info(devices[dinfo_update.Id]))
                )
                devices[dinfo_update.Id].Update(dinfo_update)

    def DeviceWatcher_Removed(sender, dinfo_update):
        if sender == watcher:
            logger.debug(
                "Removed {0}.".format(_format_device_info(devices[dinfo_update.Id]))
            )
            if dinfo_update.Id in devices:
                devices.pop(dinfo_update.Id)

    def DeviceWatcher_EnumCompleted(sender, obj):
        if sender == watcher:
            logger.debug(
                "{0} devices found. Enumeration completed. Watching for updates...".format(
                    len(devices)
                )
            )

    def DeviceWatcher_Stopped(sender, obj):
        if sender == watcher:
            logger.debug(
                "{0} devices found. Watcher status: {1}.".format(
                    len(devices), watcher.Status
                )
            )

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
            BLEDevice(
                properties["System.Devices.Aep.DeviceAddress"],
                d.Name,
                d,
                uuids=[],
                manufacturer_data=b"",
            )
        )

    return found
