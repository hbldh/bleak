import logging
import asyncio
import pathlib
from typing import List
from uuid import UUID

from bleak.backends.device import BLEDevice
from bleak.backends.dotnet.utils import BleakDataReader
from bleak.backends.scanner import BaseBleakScanner, AdvertisementData

# Import of BleakBridge to enable loading of winrt bindings
from BleakBridge import Bridge  # noqa: F401

from Windows.Devices.Bluetooth.Advertisement import (
    BluetoothLEAdvertisementWatcher,
    BluetoothLEScanningMode,
    BluetoothLEAdvertisementType,
    BluetoothLEAdvertisementReceivedEventArgs,
    BluetoothLEAdvertisementWatcherStoppedEventArgs,
)
from Windows.Foundation import TypedEventHandler

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


def _format_bdaddr(a):
    return ":".join("{:02X}".format(x) for x in a.to_bytes(6, byteorder="big"))


def _format_event_args(e):
    try:
        return "{0}: {1}".format(
            _format_bdaddr(e.BluetoothAddress), e.Advertisement.LocalName or "Unknown"
        )
    except Exception:
        return e.BluetoothAddress


class BleakScannerDotNet(BaseBleakScanner):
    """The native Windows Bleak BLE Scanner.

    Implemented using `pythonnet <https://pythonnet.github.io/>`_, a package that provides an integration to
    the .NET Common Language Runtime (CLR). Therefore, much of the code below has a distinct C# feel.

    Keyword Args:

        scanning mode (str): Set to ``Passive`` to avoid the ``Active`` scanning mode.

        SignalStrengthFilter (``Windows.Devices.Bluetooth.BluetoothSignalStrengthFilter``): A
          BluetoothSignalStrengthFilter object used for configuration of Bluetooth LE advertisement
          filtering that uses signal strength-based filtering.

        AdvertisementFilter (``Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementFilter``): A
          BluetoothLEAdvertisementFilter object used for configuration of Bluetooth LE advertisement
          filtering that uses payload section-based filtering.

    """

    def __init__(self, **kwargs):
        super(BleakScannerDotNet, self).__init__(**kwargs)

        self.watcher = None
        self._stopped_event = None
        self._devices = {}
        self._scan_responses = {}

        self._received_token = None
        self._stopped_token = None

        if "scanning_mode" in kwargs and kwargs["scanning_mode"].lower() == "passive":
            self._scanning_mode = BluetoothLEScanningMode.Passive
        else:
            self._scanning_mode = BluetoothLEScanningMode.Active

        self._signal_strength_filter = None
        self._advertisement_filter = None
        self.set_scanning_filter(**kwargs)

    def _received_handler(
        self,
        sender: BluetoothLEAdvertisementWatcher,
        event_args: BluetoothLEAdvertisementReceivedEventArgs,
    ):
        if sender == self.watcher:
            logger.debug("Received {0}.".format(_format_event_args(event_args)))
            if (
                event_args.AdvertisementType
                == BluetoothLEAdvertisementType.ScanResponse
            ):
                if event_args.BluetoothAddress not in self._scan_responses:
                    self._scan_responses[event_args.BluetoothAddress] = event_args
            else:
                if event_args.BluetoothAddress not in self._devices:
                    self._devices[event_args.BluetoothAddress] = event_args

        if self._callback is None:
            return

        # Get a "BLEDevice" from parse_event args
        device = self._parse_event_args(event_args)

        # Decode service data
        service_data = {}
        # 0x16 is service data with 16-bit UUID
        for section in event_args.Advertisement.GetSectionsByType(0x16):
            with BleakDataReader(section.Data) as reader:
                data = reader.read()
                service_data[
                    f"0000{data[1]:02x}{data[0]:02x}-0000-1000-8000-00805f9b34fb"
                ] = data[2:]
        # 0x20 is service data with 32-bit UUID
        for section in event_args.Advertisement.GetSectionsByType(0x20):
            with BleakDataReader(section.Data) as reader:
                data = reader.read()
                service_data[
                    f"{data[3]:02x}{data[2]:02x}{data[1]:02x}{data[0]:02x}-0000-1000-8000-00805f9b34fb"
                ] = data[4:]
        # 0x21 is service data with 128-bit UUID
        for section in event_args.Advertisement.GetSectionsByType(0x21):
            with BleakDataReader(section.Data) as reader:
                data = reader.read()
                service_data[str(UUID(bytes=data[15::-1]))] = data[16:]

        # Use the BLEDevice to populate all the fields for the advertisement data to return
        advertisement_data = AdvertisementData(
            local_name=event_args.Advertisement.LocalName,
            manufacturer_data=device.metadata["manufacturer_data"],
            service_data=service_data,
            service_uuids=device.metadata["uuids"],
            platform_data=(sender, event_args),
        )

        self._callback(device, advertisement_data)

    def _stopped_handler(
        self,
        sender: BluetoothLEAdvertisementWatcher,
        e: BluetoothLEAdvertisementWatcherStoppedEventArgs,
    ):
        if sender == self.watcher:
            logger.debug(
                "{0} devices found. Watcher status: {1}.".format(
                    len(self._devices), self.watcher.Status
                )
            )
            self._stopped_event.set()

    async def start(self):
        self.watcher = BluetoothLEAdvertisementWatcher()
        self.watcher.ScanningMode = self._scanning_mode

        event_loop = asyncio.get_event_loop()
        self._stopped_event = asyncio.Event()

        self._received_token = self.watcher.add_Received(
            TypedEventHandler[
                BluetoothLEAdvertisementWatcher,
                BluetoothLEAdvertisementReceivedEventArgs,
            ](
                lambda s, e: event_loop.call_soon_threadsafe(
                    self._received_handler, s, e
                )
            )
        )
        self._stopped_token = self.watcher.add_Stopped(
            TypedEventHandler[
                BluetoothLEAdvertisementWatcher,
                BluetoothLEAdvertisementWatcherStoppedEventArgs,
            ](lambda s, e: event_loop.call_soon_threadsafe(self._stopped_handler, s, e))
        )

        if self._signal_strength_filter is not None:
            self.watcher.SignalStrengthFilter = self._signal_strength_filter
        if self._advertisement_filter is not None:
            self.watcher.AdvertisementFilter = self._advertisement_filter

        self.watcher.Start()

    async def stop(self):
        self.watcher.Stop()
        await self._stopped_event.wait()

        if self._received_token:
            self.watcher.remove_Received(self._received_token)
            self._received_token = None
        if self._stopped_token:
            self.watcher.remove_Stopped(self._stopped_token)
            self._stopped_token = None

        self.watcher = None

    def set_scanning_filter(self, **kwargs):
        """Set a scanning filter for the BleakScanner.

        Keyword Args:
          SignalStrengthFilter (``Windows.Devices.Bluetooth.BluetoothSignalStrengthFilter``): A
            BluetoothSignalStrengthFilter object used for configuration of Bluetooth
            LE advertisement filtering that uses signal strength-based filtering.
          AdvertisementFilter (Windows.Devices.Bluetooth.Advertisement.BluetoothLEAdvertisementFilter): A
            BluetoothLEAdvertisementFilter object used for configuration of Bluetooth LE
            advertisement filtering that uses payload section-based filtering.

        """
        if "SignalStrengthFilter" in kwargs:
            # TODO: Handle SignalStrengthFilter parameters
            self._signal_strength_filter = kwargs["SignalStrengthFilter"]
        if "AdvertisementFilter" in kwargs:
            # TODO: Handle AdvertisementFilter parameters
            self._advertisement_filter = kwargs["AdvertisementFilter"]

    @property
    def discovered_devices(self) -> List[BLEDevice]:
        found = []
        for event_args in list(self._devices.values()):
            new_device = self._parse_event_args(event_args)
            if (
                not new_device.name
                and event_args.BluetoothAddress in self._scan_responses
            ):
                new_device.name = self._scan_responses[
                    event_args.BluetoothAddress
                ].Advertisement.LocalName
            found.append(new_device)

        return found

    @staticmethod
    def _parse_event_args(event_args):
        bdaddr = _format_bdaddr(event_args.BluetoothAddress)
        uuids = []
        for u in event_args.Advertisement.ServiceUuids:
            uuids.append(u.ToString())
        data = {}
        for m in event_args.Advertisement.ManufacturerData:
            with BleakDataReader(m.Data) as reader:
                data[m.CompanyId] = reader.read()
        local_name = event_args.Advertisement.LocalName
        rssi = event_args.RawSignalStrengthInDBm
        return BLEDevice(
            bdaddr, local_name, event_args, rssi, uuids=uuids, manufacturer_data=data
        )

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
        return self.watcher.Status if self.watcher else None
