import asyncio
from typing import List

from _bleio import Address, set_adapter
from uuid import UUID
from adafruit_ble import BLERadio
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import (
    ProvideServicesAdvertisement,
    SolicitServicesAdvertisement,
)
from bleak.backends.scanner import BaseBleakScanner, AdvertisementData


class BleakScannerCircuitPython(BaseBleakScanner):
    def __init__(
        self,
        detection_callback,
        service_uuids,
        scanning_mode,
        **kwargs,
    ):
        super().__init__(detection_callback, service_uuids)

        _adapter = kwargs.get("adapter")
        if _adapter is not None:
            # Call the global set_adapter function from _bleio
            set_adapter(_adapter)

        self._radio = BLERadio()
        self._is_active = scanning_mode == "active"
        self._loop = asyncio.get_running_loop()
        self._main_task = None
        self._is_scanning = False
        self._stop_requested = False
        self._scan_timeout = 0.2

        # We store the UUIDs to filter manually later.
        self._filter_uuids = {UUID(str(u)) for u in service_uuids} if service_uuids else None

        self._aggregated_data_cache = {}

    async def start(self):
        if self._is_scanning:
            return

        self._is_scanning = True
        self._stop_requested = False

        self._main_task = self._loop.create_task(self._scanning_task())

        await asyncio.sleep(0)

    async def stop(self):
        if not self._is_scanning:
            return

        self._stop_requested = True

        if self._main_task:
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
            self._main_task = None

    async def _scanning_task(self) -> None:
        try:
            while not self._stop_requested:
                try:
                    scan_results = self._radio.start_scan(
                        Advertisement,
                        ProvideServicesAdvertisement,
                        SolicitServicesAdvertisement,
                        timeout=self._scan_timeout,
                        active=self._is_active,
                    )

                    for advertisement in scan_results:
                        self._process_advertisement(advertisement)

                        if self._stop_requested:
                            break
                except StopIteration:
                    pass

                await asyncio.sleep(0)

        finally:
            self._radio.stop_scan()
            self._is_scanning = False
            self._aggregated_data_cache.clear()

    def _process_advertisement(self, advertisement: Advertisement) -> None:
        """
        Processes an advertisement object by aggregating its data with any
        previously seen data for the same device.
        """
        address: Address = advertisement.address
        address_string: str = ":".join(f"{b:02x}" for b in reversed(address.address_bytes))

        existing_data = self._aggregated_data_cache.get(address_string)
        current_data = self._extract_data(address_string, advertisement)

        new_local_name = current_data.local_name
        if not new_local_name and existing_data:
            new_local_name = existing_data.local_name

        new_service_uuids_set = set()
        if existing_data:
            new_service_uuids_set.update(existing_data.service_uuids)
        new_service_uuids_set.update(current_data.service_uuids)
        new_service_uuids = list(new_service_uuids_set)

        new_rssi = current_data.rssi
        new_tx_power = current_data.tx_power

        if self._matches_device_filter(new_service_uuids):

            aggregated_data = AdvertisementData(
                local_name=new_local_name,
                #manufacturer_data=new_manufacturer_data,
                manufacturer_data=None,
                #service_data=new_service_data,
                service_data={},
                service_uuids=new_service_uuids,
                tx_power=new_tx_power,
                rssi=new_rssi,
                #platform_data=new_platform_data,
                platform_data=None,
            )
            self._aggregated_data_cache[address_string] = aggregated_data

            device = self.create_or_update_device(
                key=advertisement.address,
                address=address_string,
                name=new_local_name,
                details=(self._radio, advertisement),
                adv=aggregated_data,
            )
            self.call_detection_callbacks(device, aggregated_data)

    def _extract_data(self, address_string: str, advertisement: Advertisement) -> AdvertisementData:
        """
        Helper to safely extract data from a single advertisement object,
        ensuring all mutable data is copied.
        """
        local_name = advertisement.complete_name or advertisement.short_name
        all_uuids = []
        if isinstance(advertisement, ProvideServicesAdvertisement):
            all_uuids.extend(list(advertisement.services))
        elif isinstance(advertisement, SolicitServicesAdvertisement):
            all_uuids.extend(list(advertisement.solicited_services))
        service_uuids = all_uuids

        return AdvertisementData(
            local_name=local_name,
            #manufacturer_data=manufacturer_data,
            manufacturer_data=None,
            #service_data=service_data,
            service_data={},
            service_uuids=service_uuids,
            tx_power=advertisement.tx_power,
            rssi=advertisement.rssi,
            #platform_data=(advertisement,),
            platform_data=None,
        )

    def _matches_device_filter(self, service_uuids: List[UUID, str]) -> bool:
        """
        Checks if the aggregated advertisement data contains any of the required service UUIDs.
        """
        if not self._filter_uuids:
            return True

        for service_uuid in service_uuids:
            for f_uuid in self._filter_uuids:
                if f_uuid == service_uuid:
                    return True

        return False
