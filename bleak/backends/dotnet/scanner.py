import logging
import asyncio
import pathlib
import uuid
from asyncio.events import AbstractEventLoop
from functools import wraps
from typing import Callable, Any, Union, List

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError, BleakDotNetTaskError
from bleak.backends.scanner import BaseBleakScanner

# Import of Bleak CLR->UWP Bridge. It is not needed here, but it enables loading of Windows.Devices
from BleakBridge import Bridge

from System import Array, Byte
from Windows.Devices import Enumeration
from Windows.Devices.Bluetooth.Advertisement import \
    BluetoothLEAdvertisementWatcher, BluetoothLEScanningMode, BluetoothLEAdvertisementType
from Windows.Storage.Streams import DataReader, IBuffer

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


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


class BleakScannerDotNet(BaseBleakScanner):
    """The native Windows Bleak BLE Scanner.

    Implemented using `pythonnet <https://pythonnet.github.io/>`_, a package that provides an integration to the .NET
    Common Language Runtime (CLR). Therefore, much of the code below has a distinct C# feel.

    Args:
        loop (asyncio.events.AbstractEventLoop): The event loop to use.

    Keyword Args:
        scanning mode (str): Set to "Passive" to avoid the "Active" scanning mode.

    """
    def __init__(self, loop: AbstractEventLoop = None, **kwargs):
        super(BleakScannerDotNet, self).__init__(loop, **kwargs)

        self._watcher = None
        self._devices = {}
        self._scan_responses = {}

        self._callback = None

        if "scanning_mode" in kwargs and kwargs["scanning_mode"].lower() == "passive":
            self._scanning_mode = BluetoothLEScanningMode.Passive
        else:
            self._scanning_mode = BluetoothLEScanningMode.Active

        self._signal_strength_filter = None
        self._advertisement_filter = None

    def AdvertisementWatcher_Received(self, sender, e):
        if sender == self._watcher:
            logger.debug("Received {0}.".format(_format_event_args(e)))
            if e.AdvertisementType == BluetoothLEAdvertisementType.ScanResponse:
                if e.BluetoothAddress not in self._scan_responses:
                    self._scan_responses[e.BluetoothAddress] = e
            else:
                if e.BluetoothAddress not in self._devices:
                    self._devices[e.BluetoothAddress] = e

    def AdvertisementWatcher_Stopped(self, sender, e):
        if sender == self._watcher:
            logger.debug(
                "{0} devices found. Watcher status: {1}.".format(
                    len(self._devices), self._watcher.Status
                )
            )

    async def start(self):
        self._watcher = BluetoothLEAdvertisementWatcher()
        self._watcher.ScanningMode = self._scanning_mode

        if self._callback:
            self._watcher.Received += self._callback
        else:
            self._watcher.Received += self.AdvertisementWatcher_Received
        self._watcher.Stopped += self.AdvertisementWatcher_Stopped

        # TODO: Create and set filters
        self._watcher.Start()

    async def stop(self):
        self._watcher.Stop()

        try:
            if self._callback:
                self._watcher.Received -= self._callback
            else:
                self._watcher.Received -= self.AdvertisementWatcher_Received
            self._watcher.Stopped -= self.AdvertisementWatcher_Stopped
        except Exception as e:
            logger.debug("Could not remove event handlers: {0}...".format(e))
        self._watcher = None

    async def set_scanning_filter(self, **kwargs):
        if "SignalStrengthFilter" in kwargs:
            # TODO: Handle SignalStrengthFilter parameters
            self._signal_strength_filter = kwargs["SignalStrengthFilter"]
        if "AdvertisementFilter" in kwargs:
            # TODO: Handle AdvertisementFilter parameters
            self._advertisement_filter = kwargs["AdvertisementFilter"]

    async def get_discovered_devices(self) -> List[BLEDevice]:
        found = []
        for d in list(self._devices.values()):
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
            if not local_name and d.BluetoothAddress in self._scan_responses:
                local_name = self._scan_responses[d.BluetoothAddress].Advertisement.LocalName
            found.append(
                BLEDevice(
                    bdaddr,
                    local_name,
                    d,
                    uuids=uuids,
                    manufacturer_data=data,
                )
            )

        return found

    def register_detection_callback(self, callback: Callable):
        """Set a function to act as Received Event Handler.

        Documentation for the Event Handler:
        https://docs.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.advertisement.bluetoothleadvertisementwatcher.received

        .. note::

            This replaces the regular discovery handling of this Scanner, so you have to handle storing
            and managing the returned device data yourself!

        Args:
            callback: Function accepting two arguments:
             sender (Windows.Devices.Bluetooth.AdvertisementBluetoothLEAdvertisementWatcher) and
             eventargs (Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementReceivedEventArgs)

        """
        self._callback = callback

    # Windows specific

    @property
    def status(self) -> int:
        """Get status of the Watcher.

        Returns:

            Aborted 4
            An error occurred during transition or scanning that stopped the watcher due to an error.

            Created 0
            The initial status of the watcher.

            Started 1
            The watcher is started.

            Stopped 3
            The watcher is stopped.

            Stopping 2
            The watcher stop command was issued.

        """
        return self._watcher.Status if self._watcher else None
