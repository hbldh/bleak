from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "android":
        assert False, "This backend is only available on Android"

import asyncio
import logging
from typing import Any, cast

from android.bluetooth import (
    BluetoothAdapter,
    BluetoothDevice,
    BluetoothManager,
    BluetoothProfile,
)
from android.content import Context

from bleak._compat import Self, override
from bleak.backends.adapter import BaseBleakAdapter
from bleak.backends.android.client import BleakClientAndroid
from bleak.backends.android.permissions import check_for_permissions
from bleak.backends.android.utils import context, iterate_java_obj
from bleak.backends.device import BLEDevice
from bleak.exc import (
    BleakBluetoothNotAvailableError,
    BleakBluetoothNotAvailableReason,
    BleakError,
)
from bleak.uuids import normalize_uuid_16, normalize_uuid_str

logger = logging.getLogger(__name__)

SERVICE_DISCOVERY_TIMEOUT = 10.0


class BleakAdapterAndroid(BaseBleakAdapter):
    """The Android Bleak BLE Adapter using Chaquopy/BeeWare."""

    def __init__(self, manager: BluetoothManager):
        self._manager = manager

    @classmethod
    @override
    async def get(cls, **kwargs: Any) -> Self:
        await check_for_permissions(asyncio.get_running_loop())

        if BluetoothAdapter.getDefaultAdapter() is None:
            raise BleakBluetoothNotAvailableError(
                "Bluetooth is not available",
                BleakBluetoothNotAvailableReason.NO_BLUETOOTH,
            )

        manager = cast(
            BluetoothManager, context.getSystemService(Context.BLUETOOTH_SERVICE)
        )

        return cls(manager)

    @override
    async def get_connected_devices(
        self, service_uuids: frozenset[str]
    ) -> list[BLEDevice]:
        if self._manager.getAdapter().getState() != BluetoothAdapter.STATE_ON:
            raise BleakBluetoothNotAvailableError(
                "Bluetooth is not turned on",
                BleakBluetoothNotAvailableReason.POWERED_OFF,
            )

        # Don't waste time if the default ("Generic Attribute") service is the
        # only one we're looking for since that should always match.
        check_services = service_uuids != frozenset([normalize_uuid_16(0x1801)])

        devices: list[BLEDevice] = []

        for device in iterate_java_obj(
            self._manager.getConnectedDevices(BluetoothProfile.GATT)
        ):
            address = device.getAddress()

            if check_services:
                # Android only caches the UUIDs of a few well-known services
                # (e.g. HID or hearing aids), so for anything else we have to
                # look at the GATT services ourselves.
                device_uuids = _cached_uuids(device)

                if not service_uuids & device_uuids:
                    device_uuids = await self._discover_service_uuids(address)

                if not service_uuids & device_uuids:
                    logger.debug(
                        "skipping connected device %s, no matching services in %s",
                        address,
                        sorted(device_uuids),
                    )
                    continue

            devices.append(BLEDevice(address, device.getName(), device))

        return devices

    async def _discover_service_uuids(self, address: str) -> frozenset[str]:
        """
        Get the GATT service UUIDs of a connected device.

        This opens an additional GATT client on the existing connection. Android
        serves the service discovery from its cache when the services of the
        device have already been discovered on this connection.
        """
        client = BleakClientAndroid(
            address,
            services=None,
            disconnected_callback=None,
            timeout=SERVICE_DISCOVERY_TIMEOUT,
        )

        try:
            await client.connect(pair=False)
            assert client.services is not None
            return frozenset(
                normalize_uuid_str(s.uuid) for s in client.services.services.values()
            )
        except (BleakError, asyncio.TimeoutError) as e:
            logger.debug("service discovery failed for %s: %s", address, e)
            return frozenset()
        finally:
            await client.disconnect()


def _cached_uuids(device: BluetoothDevice) -> frozenset[str]:
    """Get the service UUIDs Android has cached for a device."""
    java_uuids = device.getUuids()

    if java_uuids is None:
        return frozenset()

    return frozenset(normalize_uuid_str(str(u.getUuid())) for u in java_uuids)
