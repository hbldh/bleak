# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import List, Optional
import warnings

from typing_extensions import Literal

from bleak.backends.scanner import (
    AdvertisementDataCallback,
    BaseBleakScanner,
    AdvertisementData,
)
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from android.broadcast import BroadcastReceiver
from android.permissions import request_permissions, Permission
from jnius import cast, java_method

from . import defs
from . import utils

logger = logging.getLogger(__name__)


class BleakScannerP4Android(BaseBleakScanner):
    """
    The python-for-android Bleak BLE Scanner.

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
        detection_callback: Optional[AdvertisementDataCallback] = None,
        service_uuids: Optional[List[str]] = None,
        scanning_mode: Literal["active", "passive"] = "active",
        **kwargs,
    ):
        super(BleakScannerP4Android, self).__init__(detection_callback, service_uuids)

        if scanning_mode == "passive":
            self.__scan_mode = defs.ScanSettings.SCAN_MODE_OPPORTUNISTIC
        else:
            self.__scan_mode = defs.ScanSettings.SCAN_MODE_LOW_LATENCY

        self._devices = {}
        self.__adapter = None
        self.__javascanner = None
        self.__callback = None

    def __del__(self):
        self.__stop()

    async def start(self):
        if BleakScannerP4Android.__scanner is not None:
            raise BleakError("A BleakScanner is already scanning on this adapter.")

        logger.debug("Starting BTLE scan")

        loop = asyncio.get_running_loop()

        if self.__javascanner is None:
            if self.__callback is None:
                self.__callback = _PythonScanCallback(self, loop)

            permission_acknowledged = loop.create_future()

            def handle_permissions(permissions, grantResults):
                if any(grantResults):
                    loop.call_soon_threadsafe(
                        permission_acknowledged.set_result, grantResults
                    )
                else:
                    loop.call_soon_threadsafe(
                        permission_acknowledged.set_exception(
                            BleakError("User denied access to " + str(permissions))
                        )
                    )

            request_permissions(
                [
                    Permission.ACCESS_FINE_LOCATION,
                    Permission.ACCESS_COARSE_LOCATION,
                    "android.permission.ACCESS_BACKGROUND_LOCATION",
                ],
                handle_permissions,
            )
            await permission_acknowledged

            self.__adapter = defs.BluetoothAdapter.getDefaultAdapter()
            if self.__adapter is None:
                raise BleakError("Bluetooth is not supported on this hardware platform")
            if self.__adapter.getState() != defs.BluetoothAdapter.STATE_ON:
                raise BleakError("Bluetooth is not turned on")

            self.__javascanner = self.__adapter.getBluetoothLeScanner()

        BleakScannerP4Android.__scanner = self

        filters = cast("java.util.List", defs.List())
        if self._service_uuids:
            for uuid in self._service_uuids:
                filters.add(
                    defs.ScanFilterBuilder()
                    .setServiceUuid(defs.ParcelUuid.fromString(uuid))
                    .build()
                )

        scanfuture = self.__callback.perform_and_wait(
            dispatchApi=self.__javascanner.startScan,
            dispatchParams=(
                filters,
                defs.ScanSettingsBuilder()
                .setScanMode(self.__scan_mode)
                .setReportDelay(0)
                .setPhy(defs.ScanSettings.PHY_LE_ALL_SUPPORTED)
                .setNumOfMatches(defs.ScanSettings.MATCH_NUM_MAX_ADVERTISEMENT)
                .setMatchMode(defs.ScanSettings.MATCH_MODE_AGGRESSIVE)
                .setCallbackType(defs.ScanSettings.CALLBACK_TYPE_ALL_MATCHES)
                .build(),
                self.__callback.java,
            ),
            resultApi="onScan",
            return_indicates_status=False,
        )
        self.__javascanner.flushPendingScanResults(self.__callback.java)

        try:
            await asyncio.wait_for(scanfuture, timeout=0.2)
        except asyncio.exceptions.TimeoutError:
            pass
        except BleakError as bleakerror:
            await self.stop()
            if bleakerror.args != (
                "onScan",
                "SCAN_FAILED_APPLICATION_REGISTRATION_FAILED",
            ):
                raise bleakerror
            else:
                # there might be a clearer solution to this if android source and vendor
                # documentation are reviewed for the meaning of the error
                # https://stackoverflow.com/questions/27516399/solution-for-ble-scans-scan-failed-application-registration-failed
                warnings.warn(
                    "BT API gave SCAN_FAILED_APPLICATION_REGISTRATION_FAILED.  Resetting adapter."
                )

                def handlerWaitingForState(state, stateFuture):
                    def handleAdapterStateChanged(context, intent):
                        adapter_state = intent.getIntExtra(
                            defs.BluetoothAdapter.EXTRA_STATE,
                            defs.BluetoothAdapter.STATE_ERROR,
                        )
                        if adapter_state == defs.BluetoothAdapter.STATE_ERROR:
                            loop.call_soon_threadsafe(
                                stateOffFuture.set_exception,
                                BleakError(f"Unexpected adapter state {adapter_state}"),
                            )
                        elif adapter_state == state:
                            loop.call_soon_threadsafe(
                                stateFuture.set_result, adapter_state
                            )

                    return handleAdapterStateChanged

                logger.info(
                    "disabling bluetooth adapter to handle SCAN_FAILED_APPLICATION_REGSTRATION_FAILED ..."
                )
                stateOffFuture = loop.create_future()
                receiver = BroadcastReceiver(
                    handlerWaitingForState(
                        defs.BluetoothAdapter.STATE_OFF, stateOffFuture
                    ),
                    actions=[defs.BluetoothAdapter.ACTION_STATE_CHANGED],
                )
                receiver.start()
                try:
                    self.__adapter.disable()
                    await stateOffFuture
                finally:
                    receiver.stop()

                logger.info("re-enabling bluetooth adapter ...")
                stateOnFuture = loop.create_future()
                receiver = BroadcastReceiver(
                    handlerWaitingForState(
                        defs.BluetoothAdapter.STATE_ON, stateOnFuture
                    ),
                    actions=[defs.BluetoothAdapter.ACTION_STATE_CHANGED],
                )
                receiver.start()
                try:
                    self.__adapter.enable()
                    await stateOnFuture
                finally:
                    receiver.stop()
                logger.debug("restarting scan ...")

                return await self.start()

    def __stop(self):
        if self.__javascanner is not None:
            logger.debug("Stopping BTLE scan")
            self.__javascanner.stopScan(self.__callback.java)
            BleakScannerP4Android.__scanner = None
            self.__javascanner = None
        else:
            logger.debug("BTLE scan already stopped")

    async def stop(self):
        self.__stop()

    def set_scanning_filter(self, **kwargs):
        # If we do end up implementing this, this should accept List<ScanFilter>
        # and ScanSettings java objects to pass to startScan().
        raise NotImplementedError("not implemented in Android backend")

    @property
    def discovered_devices(self) -> List[BLEDevice]:
        return [*self._devices.values()]


class _PythonScanCallback(utils.AsyncJavaCallbacks):
    __javainterfaces__ = ["com.github.hbldh.bleak.PythonScanCallback$Interface"]

    def __init__(self, scanner, loop):
        super().__init__(loop)
        self._scanner = scanner
        self.java = defs.PythonScanCallback(self)

    def result_state(self, status_str, name, *data):
        self._loop.call_soon_threadsafe(
            self._result_state_unthreadsafe, status_str, name, data
        )

    @java_method("(I)V")
    def onScanFailed(self, errorCode):
        self.result_state(defs.ScanFailed(errorCode).name, "onScan")

    @java_method("(Landroid/bluetooth/le/ScanResult;)V")
    def onScanResult(self, result):
        device = result.getDevice()
        record = result.getScanRecord()

        service_uuids = record.getServiceUuids()
        if service_uuids is not None:
            service_uuids = [service_uuid.toString() for service_uuid in service_uuids]

        manufacturer_data = record.getManufacturerSpecificData()
        manufacturer_data = {
            manufacturer_data.keyAt(index): bytes(manufacturer_data.valueAt(index))
            for index in range(manufacturer_data.size())
        }

        service_data = {
            entry.getKey().toString(): bytes(entry.getValue())
            for entry in record.getServiceData().entrySet()
        }

        advertisement = AdvertisementData(
            local_name=record.getDeviceName(),
            manufacturer_data=manufacturer_data,
            service_data=service_data,
            service_uuids=service_uuids,
            platform_data=(result,),
        )
        device = BLEDevice(
            device.getAddress(),
            device.getName(),
            rssi=result.getRssi(),
            uuids=service_uuids,
            manufacturer_data=manufacturer_data,
        )
        self._scanner._devices[device.address] = device
        if "onScan" not in self.states:
            self.result_state(None, "onScan", device)
        if self._scanner._callback:
            self._loop.call_soon_threadsafe(
                self._scanner._callback, device, advertisement
            )
