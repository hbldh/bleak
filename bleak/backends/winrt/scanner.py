import asyncio
import logging
from typing import Dict, List, NamedTuple, Optional
from uuid import UUID

from bleak_winrt.windows.devices.bluetooth.advertisement import (
    BluetoothLEScanningMode,
    BluetoothLEAdvertisementWatcher,
    BluetoothLEAdvertisementReceivedEventArgs,
    BluetoothLEAdvertisementType,
)
from typing_extensions import Literal

from ..device import BLEDevice
from ..scanner import AdvertisementDataCallback, BaseBleakScanner, AdvertisementData
from ...assigned_numbers import AdvertisementDataType


logger = logging.getLogger(__name__)


def _format_bdaddr(a):
    return ":".join("{:02X}".format(x) for x in a.to_bytes(6, byteorder="big"))


def _format_event_args(e):
    try:
        return "{0}: {1}".format(
            _format_bdaddr(e.bluetooth_address), e.advertisement.local_name or "Unknown"
        )
    except Exception:
        return e.bluetooth_address


class _RawAdvData(NamedTuple):
    """
    Platform-specific advertisement data.

    Windows does not combine advertising data with type SCAN_RSP with other
    advertising data like other platforms, so se have to do it ourselves.
    """

    adv: BluetoothLEAdvertisementReceivedEventArgs
    """
    The advertisement data received from the BluetoothLEAdvertisementWatcher.Received event.
    """
    scan: Optional[BluetoothLEAdvertisementReceivedEventArgs]
    """
    The scan response for the same device as *adv*.
    """


class BleakScannerWinRT(BaseBleakScanner):
    """The native Windows Bleak BLE Scanner.

    Implemented using `Python/WinRT <https://github.com/Microsoft/xlang/tree/master/src/package/pywinrt/projection/>`_.

    Args:
        detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
        service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received.
        scanning_mode:
            Set to ``"passive"`` to avoid the ``"active"`` scanning mode.

    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback] = None,
        service_uuids: Optional[List[str]] = None,
        scanning_mode: Literal["active", "passive"] = "active",
        **kwargs,
    ):
        super(BleakScannerWinRT, self).__init__(detection_callback, service_uuids)

        self.watcher = None
        self._stopped_event = None
        self._discovered_devices: Dict[int, _RawAdvData] = {}

        # case insensitivity is for backwards compatibility on Windows only
        if scanning_mode.lower() == "passive":
            self._scanning_mode = BluetoothLEScanningMode.PASSIVE
        else:
            self._scanning_mode = BluetoothLEScanningMode.ACTIVE

        self._signal_strength_filter = kwargs.get("SignalStrengthFilter", None)
        self._advertisement_filter = kwargs.get("AdvertisementFilter", None)

        self._received_token = None
        self._stopped_token = None

    def _received_handler(
        self,
        sender: BluetoothLEAdvertisementWatcher,
        event_args: BluetoothLEAdvertisementReceivedEventArgs,
    ):
        """Callback for AdvertisementWatcher.Received"""
        # TODO: Cannot check for if sender == self.watcher in winrt?
        logger.debug("Received {0}.".format(_format_event_args(event_args)))

        # get the previous advertising data or start a new one
        raw_data = self._discovered_devices.get(
            event_args.bluetooth_address, _RawAdvData(event_args, None)
        )

        # update the advertsing data depending on the advertising data type
        if event_args.advertisement_type == BluetoothLEAdvertisementType.SCAN_RESPONSE:
            raw_data = _RawAdvData(raw_data.adv, event_args)
        else:
            raw_data = _RawAdvData(event_args, raw_data.scan)

        self._discovered_devices[event_args.bluetooth_address] = raw_data

        if self._callback is None:
            return

        # Get a "BLEDevice" from parse_event args
        device = self._parse_adv_data(raw_data)

        # On Windows, we have to fake service UUID filtering. If we were to pass
        # a BluetoothLEAdvertisementFilter to the BluetoothLEAdvertisementWatcher
        # with the service UUIDs appropriately set, we would no longer receive
        # scan response data (which commonly contains the local device name).
        # So we have to do it like this instead.

        if self._service_uuids:
            for uuid in device.metadata["uuids"]:
                if uuid in self._service_uuids:
                    break
            else:
                # if there were no matching service uuids, the don't call the callback
                return

        service_data = {}

        # Decode service data
        for args in filter(lambda d: d is not None, raw_data):
            for section in args.advertisement.get_sections_by_type(
                AdvertisementDataType.SERVICE_DATA_UUID16
            ):
                data = bytes(section.data)
                service_data[
                    f"0000{data[1]:02x}{data[0]:02x}-0000-1000-8000-00805f9b34fb"
                ] = data[2:]
            for section in args.advertisement.get_sections_by_type(
                AdvertisementDataType.SERVICE_DATA_UUID32
            ):
                data = bytes(section.data)
                service_data[
                    f"{data[3]:02x}{data[2]:02x}{data[1]:02x}{data[0]:02x}-0000-1000-8000-00805f9b34fb"
                ] = data[4:]
            for section in args.advertisement.get_sections_by_type(
                AdvertisementDataType.SERVICE_DATA_UUID128
            ):
                data = bytes(section.data)
                service_data[str(UUID(bytes=bytes(data[15::-1])))] = data[16:]

        # Use the BLEDevice to populate all the fields for the advertisement data to return
        advertisement_data = AdvertisementData(
            local_name=device.name,
            manufacturer_data=device.metadata["manufacturer_data"],
            service_data=service_data,
            service_uuids=device.metadata["uuids"],
            platform_data=(sender, raw_data),
        )

        self._callback(device, advertisement_data)

    def _stopped_handler(self, sender, e):
        logger.debug(
            "{0} devices found. Watcher status: {1}.".format(
                len(self._discovered_devices), self.watcher.status
            )
        )
        self._stopped_event.set()

    async def start(self):
        # start with fresh list of discovered devices
        self._discovered_devices.clear()

        self.watcher = BluetoothLEAdvertisementWatcher()
        self.watcher.scanning_mode = self._scanning_mode

        event_loop = asyncio.get_running_loop()
        self._stopped_event = asyncio.Event()

        self._received_token = self.watcher.add_received(
            lambda s, e: event_loop.call_soon_threadsafe(self._received_handler, s, e)
        )
        self._stopped_token = self.watcher.add_stopped(
            lambda s, e: event_loop.call_soon_threadsafe(self._stopped_handler, s, e)
        )

        if self._signal_strength_filter is not None:
            self.watcher.signal_strength_filter = self._signal_strength_filter
        if self._advertisement_filter is not None:
            self.watcher.advertisement_filter = self._advertisement_filter

        self.watcher.start()

    async def stop(self):
        self.watcher.stop()
        await self._stopped_event.wait()

        try:
            self.watcher.remove_received(self._received_token)
            self.watcher.remove_stopped(self._stopped_token)
        except Exception as e:
            logger.debug("Could not remove event handlers: {0}...".format(e))

        self._stopped_token = None
        self._received_token = None

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
        return [self._parse_adv_data(d) for d in self._discovered_devices.values()]

    @staticmethod
    def _parse_adv_data(raw_data: _RawAdvData) -> BLEDevice:
        """
        Combines advertising data from regular advertisement data and scan response.
        """
        bdaddr = _format_bdaddr(raw_data.adv.bluetooth_address)
        uuids = []
        data = {}
        local_name = None

        for args in filter(lambda d: d is not None, raw_data):
            for u in args.advertisement.service_uuids:
                uuids.append(str(u))
            for m in args.advertisement.manufacturer_data:
                data[m.company_id] = bytes(m.data)
            # local name is empty string rather than None if not present
            if args.advertisement.local_name:
                local_name = args.advertisement.local_name
            rssi = args.raw_signal_strength_in_d_bm

        return BLEDevice(
            bdaddr, local_name, raw_data, rssi, uuids=uuids, manufacturer_data=data
        )
