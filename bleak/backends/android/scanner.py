from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import asyncio
import dataclasses
import logging
from typing import Any, Literal, Optional

from android.bluetooth import BluetoothAdapter
from android.bluetooth.le import (
    BluetoothLeScanner,
    ScanFilter,
    ScanResult,
    ScanSettings,
)
from android.os import ParcelUuid
from java.util import ArrayList, HashMap

from bleak._compat import override
from bleak.backends.android.dispatcher import dispatch_func
from bleak.backends.android.permissions import check_for_permissions
from bleak.backends.android.scanner_callback import OnScanCallback, PythonScanCallback
from bleak.backends.android.utils import iterate_java_obj
from bleak.backends.scanner import (
    AdvertisementData,
    AdvertisementDataCallback,
    BaseBleakScanner,
)
from bleak.exc import (
    BleakBluetoothNotAvailableError,
    BleakBluetoothNotAvailableReason,
    BleakError,
)

logger = logging.getLogger(__name__)

NUM_SCAN_DURATIONS_KEPT = 5
EXCESSIVE_SCANNING_PERIOD = 30.5  # normally 30s, add 0.5s margin


class ExcessiveUsageChecker:
    """
    On Android, no more than 5 start/stop scanning operations are allowed per 30 seconds!

    This is a helper class to track scan start times and enforce waiting if excessive scanning is detected.

    See this commit: https://android-review.googlesource.com/c/platform/packages/apps/Bluetooth/+/215844
    Or this comment: https://github.com/NordicSemiconductor/Android-Scanner-Compat-Library/issues/18#issuecomment-402412139
    """

    def __init__(self) -> None:
        self.scan_timestamps: list[float] = []

    def add_new_scan(self, loop: asyncio.AbstractEventLoop) -> None:
        """Record a new scan start time."""
        self.scan_timestamps.append(loop.time())
        if len(self.scan_timestamps) > NUM_SCAN_DURATIONS_KEPT:
            self.scan_timestamps.pop(0)

    async def wait_if_excessive(self, loop: asyncio.AbstractEventLoop) -> None:
        """Wait if excessive scanning is detected."""
        if len(self.scan_timestamps) < NUM_SCAN_DURATIONS_KEPT:
            return

        period = loop.time() - self.scan_timestamps[0]
        if (waiting_time := EXCESSIVE_SCANNING_PERIOD - period) > 0:
            logger.warning(
                f"Excessive scanning detected: last {NUM_SCAN_DURATIONS_KEPT} scans in {period:.2f} seconds. waiting {waiting_time:.2f} seconds"
            )
            await asyncio.sleep(waiting_time)


excessive_usage_checker = ExcessiveUsageChecker()


@dataclasses.dataclass
class ScanObjects:
    adapter: BluetoothAdapter
    javascanner: BluetoothLeScanner
    callback: PythonScanCallback


class BleakScannerAndroid(BaseBleakScanner):
    """Android Bleak BLE Scanner using Chaquopy/BeeWare.

    Args:
        detection_callback:
            Optional function that will be called each time a device is
            discovered or advertising data has changed.
        service_uuids:
            Optional list of service UUIDs to filter on. Only advertisements
            containing this advertising data will be received. Specifying this
            also enables scanning while the screen is off on Android.
        scanning_mode:
            Set to ``"passive"`` to avoid the ``"active"`` scanning mode.
    """

    __scanner = None

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback],
        service_uuids: Optional[list[str]],
        scanning_mode: Literal["active", "passive"],
        **kwargs: Any,
    ):
        super(BleakScannerAndroid, self).__init__(detection_callback, service_uuids)

        self._loop = asyncio.get_running_loop()

        if scanning_mode == "passive":
            self.__scan_mode = ScanSettings.SCAN_MODE_OPPORTUNISTIC
        else:
            self.__scan_mode = ScanSettings.SCAN_MODE_LOW_LATENCY

        self._scan_objs: Optional[ScanObjects] = None

    @override
    async def start(self) -> None:
        if BleakScannerAndroid.__scanner is not None:
            raise BleakError("A BleakScanner is already scanning on this adapter.")

        logger.debug("Starting BTLE scan")

        if self._scan_objs is None:
            callback = PythonScanCallback(self, self._loop)

            await check_for_permissions(self._loop)

            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None:
                raise BleakBluetoothNotAvailableError(
                    "Bluetooth is not available",
                    BleakBluetoothNotAvailableReason.NO_BLUETOOTH,
                )
            if adapter.getState() != BluetoothAdapter.STATE_ON:
                raise BleakBluetoothNotAvailableError(
                    "Bluetooth is not turned on",
                    BleakBluetoothNotAvailableReason.POWERED_OFF,
                )

            javascanner = adapter.getBluetoothLeScanner()
            if javascanner is None:
                raise BleakBluetoothNotAvailableError(
                    "Bluetooth LE scanning is not available",
                    BleakBluetoothNotAvailableReason.POWERED_OFF,
                )

            self._scan_objs = ScanObjects(
                adapter=adapter,
                javascanner=javascanner,
                callback=callback,
            )

        BleakScannerAndroid.__scanner = self

        await excessive_usage_checker.wait_if_excessive(self._loop)
        excessive_usage_checker.add_new_scan(self._loop)

        filters: ArrayList[ScanFilter] = ArrayList()
        if self._service_uuids:
            for uuid in self._service_uuids:
                filter = (
                    ScanFilter.Builder()
                    .setServiceUuid(ParcelUuid.fromString(uuid))
                    .build()
                )
                filters.add(filter)

        settings = (
            ScanSettings.Builder()
            .setScanMode(self.__scan_mode)
            .setReportDelay(0)
            .setPhy(ScanSettings.PHY_LE_ALL_SUPPORTED)
            .setNumOfMatches(ScanSettings.MATCH_NUM_MAX_ADVERTISEMENT)
            .setMatchMode(ScanSettings.MATCH_MODE_AGGRESSIVE)
            .setCallbackType(ScanSettings.CALLBACK_TYPE_ALL_MATCHES)
            .build()
        )
        scanfuture = self._scan_objs.callback.dispatcher.perform_and_wait(
            dispatch_func=dispatch_func(
                self._scan_objs.javascanner.startScan,
                filters,
                settings,
                self._scan_objs.callback.java,
            ),
            callback_api=OnScanCallback(),
            dispatch_result_indicates_status=False,
        )

        try:
            # Wait a short time to check if "onScanFailed" is called.
            await asyncio.wait_for(scanfuture, timeout=0.2)
        except asyncio.exceptions.TimeoutError:
            # If the scan started successfully but no device is found in the
            # short waiting period, a timeout occurs. This is not an error.
            pass

    @override
    async def stop(self) -> None:
        if self._scan_objs is None:
            logger.debug("BTLE scan already stopped")
            return

        logger.debug("Stopping BTLE scan")
        self._scan_objs.javascanner.stopScan(self._scan_objs.callback.java)
        BleakScannerAndroid.__scanner = None
        self._scan_objs = None

    def handle_scan_result(self, result: ScanResult) -> None:
        native_device = result.getDevice()
        record = result.getScanRecord()
        assert record is not None

        java_service_uuids = record.getServiceUuids()
        if java_service_uuids is None:
            service_uuids = []
        else:
            service_uuids = [
                str(service_uuid)
                for service_uuid in iterate_java_obj(java_service_uuids)
            ]

        if not self.is_allowed_uuid(service_uuids):
            return

        java_manufacturer_data = record.getManufacturerSpecificData()
        assert java_manufacturer_data is not None
        manufacturer_data = {
            java_manufacturer_data.keyAt(index): bytes(
                java_manufacturer_data.valueAt(index)
            )
            for index in range(java_manufacturer_data.size())
        }

        # "getServiceData()"" returns an "ArrayMap". An "ArrayMap" has no valid
        # "entrySet()" Method. So we have to convert it to a HashMap first.
        service_data_set = HashMap(record.getServiceData()).entrySet()
        service_data: dict[str, bytes] = {
            str(entry.getKey()): bytes(entry.getValue())
            for entry in iterate_java_obj(service_data_set)
        }

        tx_power: int | None = record.getTxPowerLevel()

        # change "not present" value to None to match other backends
        if tx_power == -2147483648:  # Integer#MIN_VALUE
            tx_power = None

        advertisement = AdvertisementData(
            local_name=record.getDeviceName(),
            manufacturer_data=manufacturer_data,
            service_data=service_data,
            service_uuids=service_uuids,
            tx_power=tx_power,
            rssi=result.getRssi(),
            platform_data=(result,),
        )

        device = self.create_or_update_device(
            native_device.getAddress(),
            native_device.getAddress(),
            native_device.getName(),
            native_device,
            advertisement,
        )

        self.call_detection_callbacks(device, advertisement)
