#!/usr/bin/env python

"""Tests for `bleak.backends.bumble` package, specifically scanning and advertising functionality."""

from asyncio import Queue
from typing import Tuple

import pytest
from bumble.device import AdvertisingData, AdvertisingType

from bleak.backends.bumble.scanner import BleakScannerBumble
from bleak.backends.scanner import AdvertisementData, BLEDevice
from tests.bleak.backends.bumble.test_utils import get_device, test_transport

adv_data_queue: Queue[Tuple[BLEDevice, AdvertisementData]] = Queue()

ADV_PARAMS = {"name": "scan_dev", "addr": "12:34:56:78:AB:CD"}


async def adv_cb(device: BLEDevice, data: AdvertisementData) -> None:
    """Callback to handle BLE device and advertisement data."""
    await adv_data_queue.put((device, data))


@pytest.mark.asyncio
async def test_adv_data():
    """Test to validate that advertisement data can be detected correctly."""
    scan_dev = get_device(ADV_PARAMS["addr"])
    adv_name_data = AdvertisingData(
        [(AdvertisingData.COMPLETE_LOCAL_NAME, ADV_PARAMS["name"].encode("utf-8"))]
    )
    await scan_dev.power_on()
    await scan_dev.start_advertising(
        advertising_type=AdvertisingType.UNDIRECTED,
        target=None,
        advertising_data=bytes(adv_name_data),
    )

    scanner = BleakScannerBumble(
        detection_callback=adv_cb,
        service_uuids=None,
        scanning_mode="active",
        cfg=test_transport,
    )

    await scanner.start()
    device, data = await adv_data_queue.get()
    assert device.name == ADV_PARAMS["name"]
    assert device.address == ADV_PARAMS["addr"]
