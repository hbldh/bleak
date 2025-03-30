#!/usr/bin/env python

"""Tests for `bleak.backends.bumble` package, specifically connection functionality."""

from asyncio import Queue
from typing import Tuple

import pytest
from bumble.gatt import Characteristic, Service

from bleak.backends.bumble.client import BleakClientBumble
from bleak.backends.scanner import AdvertisementData, BLEDevice
from tests.bleak.backends.bumble.test_utils import get_device, test_transport

adv_data_queue: Queue[Tuple[BLEDevice, AdvertisementData]] = Queue()

CONN_ADDR = "12:34:56:78:AB:CD"


@pytest.mark.asyncio
async def test_service():
    SVC_UUID = "50DB505C-8AC4-4738-8448-3B1D9CC09CC5"
    CHAR_UUID = "486F64C6-4B5F-4B3B-8AFF-EDE134A8446A"
    CHAR_VAL = "hello"
    svc1 = Service(
        SVC_UUID,
        [
            Characteristic(
                CHAR_UUID,
                Characteristic.Properties.READ | Characteristic.Properties.NOTIFY,
                Characteristic.READABLE,
                CHAR_VAL,
            ),
        ],
    )
    conn_dev = get_device(CONN_ADDR)
    conn_dev.add_services([svc1])
    await conn_dev.power_on()

    client = BleakClientBumble(CONN_ADDR, cfg=test_transport)
    await client.connect()
    svc_found = False
    for svc in client.services:
        if svc.uuid == svc1.uuid:
            svc_found = True
            break
    assert svc_found
    val = await client.read_gatt_char(CHAR_UUID)
    assert val.decode("utf-8") == CHAR_VAL
