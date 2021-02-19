import asyncio
import logging
import pathlib
from typing import Callable, List
from uuid import UUID

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import BaseBleakScanner, AdvertisementData

import winrt.windows.devices.bluetooth.advertisement as winbleadv
import winrt.windows.storage.streams as winstrm


logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent


def _format_bdaddr(a):
    return ":".join("{:02X}".format(x) for x in a.to_bytes(6, byteorder="big"))


def _format_event_args(e):
    try:
        return "{0}: {1}".format(
            _format_bdaddr(e.bluetooth_address), e.advertisement.local_name or "Unknown"
        )
    except Exception:
        return e.bluetooth_address


class BleakScannerWinRT(BaseBleakScanner):
    """The native Windows Bleak BLE Scanner.

    Implemented using `Python/WinRT <https://github.com/Microsoft/xlang/tree/master/src/package/pywinrt/projection/>`_.

    Keyword Args:
        scanning mode (str): Set to "Passive" to avoid the "Active" scanning mode.

    """

    def __init__(self, **kwargs):
        super(BleakScannerWinRT, self).__init__(**kwargs)

        self.watcher = None
        self._devices = {}
        self._scan_responses = {}

        if "scanning_mode" in kwargs and kwargs["scanning_mode"].lower() == "passive":
            self._scanning_mode = winbleadv.BluetoothLEScanningMode.PASSIVE
        else:
            self._scanning_mode = winbleadv.BluetoothLEScanningMode.ACTIVE

        self._signal_strength_filter = kwargs.get("SignalStrengthFilter", None)
        self._advertisement_filter = kwargs.get("AdvertisementFilter", None)

        self._received_token = None
        self._stopped_token = None

    def _received_handler(
        self,
        sender: winbleadv.BluetoothLEAdvertisementWatcher,
        event_args: winbleadv.BluetoothLEAdvertisementReceivedEventArgs,
    ):
        """Callback for AdvertisementWatcher.Received"""
        # TODO: Cannot check for if sender == self.watcher in winrt?
        logger.debug("Received {0}.".format(_format_event_args(event_args)))
        if (
            event_args.advertisement_type
            == winbleadv.BluetoothLEAdvertisementType.SCAN_RESPONSE
        ):
            if event_args.bluetooth_address not in self._scan_responses:
                self._scan_responses[event_args.bluetooth_address] = event_args
        else:
            if event_args.bluetooth_address not in self._devices:
                self._devices[event_args.bluetooth_address] = event_args

        if self._callback is None:
            return

        # Get a "BLEDevice" from parse_event args
        device = self.parse_eventargs(event_args)

        # Decode service data
        service_data = {}
        # 0x16 is service data with 16-bit UUID
        for section in event_args.advertisement.get_sections_by_type(0x16):
            # TODO: Figure out how to use read_bytes instead...
            reader = winstrm.DataReader.from_buffer(section.data)
            data = [reader.read_byte() for _ in range(section.data.length)]
            service_data[
                f"0000{data[1]:02x}{data[0]:02x}-0000-1000-8000-00805f9b34fb"
            ] = data[2:]
        # 0x20 is service data with 32-bit UUID
        for section in event_args.advertisement.get_sections_by_type(0x20):
            reader = winstrm.DataReader.from_buffer(section.data)
            data = [reader.read_byte() for _ in range(section.data.length)]
            service_data[
                f"{data[3]:02x}{data[2]:02x}{data[1]:02x}{data[0]:02x}-0000-1000-8000-00805f9b34fb"
            ] = data[4:]
        # 0x21 is service data with 128-bit UUID
        for section in event_args.advertisement.get_sections_by_type(0x21):
            reader = winstrm.DataReader.from_buffer(section.data)
            data = [reader.read_byte() for _ in range(section.data.length)]
            service_data[str(UUID(bytes=data[15::-1]))] = data[16:]

        # Use the BLEDevice to populate all the fields for the advertisement data to return
        advertisement_data = AdvertisementData(
            local_name=event_args.advertisement.local_name,
            manufacturer_data=device.metadata["manufacturer_data"],
            service_data=service_data,
            service_uuids=device.metadata["uuids"],
            platform_data=(sender, event_args),
        )

        self._callback(device, advertisement_data)

    def _stopped_handler(self, sender, e):
        logger.debug(
            "{0} devices found. Watcher status: {1}.".format(
                len(self._devices), self.watcher.status
            )
        )

    async def start(self):
        self.watcher = winbleadv.BluetoothLEAdvertisementWatcher()
        self.watcher.scanning_mode = self._scanning_mode

        event_loop = asyncio.get_event_loop()

        self._received_token = self.watcher.add_received(
            lambda s, e: event_loop.call_soon_threadsafe(self._received_handler, s, e)
        )
        self._stopped_token = self.watcher.add_stopped(
            lambda s, e: event_loop.call_soon_threadsafe(self._stopped_handler, s, e)
        )

        if self._signal_strength_filter is not None:
            self.watcher.signal_strength_filter = self._signal_strength_filter
        if self._advertisement_filter is not None:
            self.watcher._advertisement_filter = self._advertisement_filter

        self.watcher.start()

    async def stop(self):
        self.watcher.stop()

        try:
            self.watcher.remove_received(self._received_token)
            self.watcher.remove_stopped(self._stopped_token)
        except Exception as e:
            logger.debug("Could not remove event handlers: {0}...".format(e))

        self._stopped_token = None
        self._received_token = None

        self.watcher = None

    async def set_scanning_filter(self, **kwargs):
        pass

    async def get_discovered_devices(self) -> List[BLEDevice]:
        found = []
        for event_args in list(self._devices.values()):
            new_device = self.parse_eventargs(event_args)
            if (
                not new_device.name
                and event_args.bluetooth_address in self._scan_responses
            ):
                new_device.name = self._scan_responses[
                    event_args.bluetooth_address
                ].advertisement.local_name
            found.append(new_device)

        return found

    def parse_eventargs(self, event_args):
        bdaddr = _format_bdaddr(event_args.bluetooth_address)
        uuids = []
        try:
            for u in event_args.advertisement.service_uuids:
                uuids.append(str(u))
        except NotImplementedError as e:
            # Cannot get service uuids for this device...
            pass
        data = {}
        for m in event_args.advertisement.manufacturer_data:
            # TODO: Figure out how to use read_bytes instead...
            reader = winstrm.DataReader.from_buffer(m.data)
            b = [reader.read_byte() for _ in range(m.data.length)]
            data[m.company_id] = bytes(b)
        local_name = event_args.advertisement.local_name
        return BLEDevice(
            bdaddr, local_name, event_args, uuids=uuids, manufacturer_data=data
        )
