# Test the context manager (with statement)

# Python: Requires alt-pytest-asyncio  (timeouts and asynchio)
# Micro:bit:  Be sure they are running a recent version of firmware (0253 or later)
#       https://microbit.org/get-started/user-guide/firmware/


import logging
import os
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logger = logging.getLogger(__name__)

import asyncio
import pytest
from common_fixtures import *
from time import time
from math import floor

### Actual Tests! ###

@pytest.mark.async_timeout(10)
async def test_scan_find(configure_firmware):
    # Scan and count devices...there should be at least the one device
    count = 0

    def detection_callback(device):
        nonlocal count 
        count += 1

    scanner = bleak.BleakScanner()
    scanner.register_detection_callback(detection_callback)
    await scanner.start()
    await asyncio.sleep(3.0)
    await scanner.stop()
    devices = await scanner.get_discovered_devices()

    assert len(devices) > 0
    # Check callback calls 
    assert len(devices) == count


@pytest.mark.async_timeout(10)
async def test_scan_by_service_UUID(configure_firmware):
    # Scan and count devices...there should be at least the one device
    count = 0

    def detection_callback(device):
        nonlocal count 
        count += 1

    scanner = bleak.BleakScanner(filters={"UUIDs":["1d93af38-9239-11ea-bb37-0242ac130002"], "DuplicateData":False})
    scanner.register_detection_callback(detection_callback)
    await scanner.start()
    await asyncio.sleep(3.0)
    await scanner.stop()
    devices = await scanner.get_discovered_devices()

    assert len(devices) > 0
    # Check callback calls 
    assert len(devices) == count

    for d in devices:
        assert d.metadata['uuids'] != None 
        assert '1d93af38-9239-11ea-bb37-0242ac130002' in d.metadata['uuids']


@pytest.mark.async_timeout(10)
async def test_scan_by_service_UUID(configure_firmware):
    # Scan and count devices...there should be at least the one device
    count = 0

    def detection_callback(device):
        nonlocal count 
        count += 1

    scanner = bleak.BleakScanner(filters={"UUIDs":["1d93af38-9239-11ea-bb37-0242ac130002"], "DuplicateData":False})
    scanner.register_detection_callback(detection_callback)
    await scanner.start()
    await asyncio.sleep(3.0)
    await scanner.stop()
    devices = await scanner.get_discovered_devices()

    assert len(devices) > 0
    # Check callback calls 
    assert len(devices) == count

    for d in devices:
        assert d.metadata['uuids'] != None 
        assert '1d93af38-9239-11ea-bb37-0242ac130002' in d.metadata['uuids']


@pytest.mark.async_timeout(30)
async def test_scan_by_service_two_devs(configure_firmware, configure_firmware2):
    # Scan and count devices...there should be at least the one device
    count = 0

    def detection_callback(device):
        nonlocal count 
        count += 1

    scanner = bleak.BleakScanner(filters={"UUIDs":["1d93af38-9239-11ea-bb37-0242ac130002"], "DuplicateData":False})
    scanner.register_detection_callback(detection_callback)
    await scanner.start()
    await asyncio.sleep(3.0)
    await scanner.stop()
    devices = await scanner.get_discovered_devices()

    assert len(devices) == 2 
    # Check callback calls 
    assert len(devices) == count

    for d in devices:
        assert d.metadata['uuids'] != None 
        assert '1d93af38-9239-11ea-bb37-0242ac130002' in d.metadata['uuids']

@pytest.mark.async_timeout(30)
async def test_scan_device_name(configure_firmware, configure_firmwareB2):
    # Scan and count devices...there should be at least the one device
    count = 0

    def detection_callback(device):
        if device.name == "Test MB2":
            print(f"Device: {device}")
            assert 'txpwr' in device.metadata
            assert device.metadata['txpwr'] == -100
            nonlocal count 
            count += 1

    scanner = bleak.BleakScanner(filters={"DuplicateData":False})
    scanner.register_detection_callback(detection_callback)
    await scanner.start()
    await asyncio.sleep(5.0)
    await scanner.stop()
    devices = await scanner.get_discovered_devices()

    # macOS finds it twice --- TODO: Review why....Details changing??
    assert count > 0 and count <= 2

    for d in devices:
        if d.name == "Test MB2":
            assert 'txpwr' in d.metadata
            assert d.metadata['txpwr'] == -100

@pytest.mark.async_timeout(30)
async def test_scan_high_rssi(configure_firmware):
    # The RSSI filter is HIGH and nothing should match
    count = 0

    def detection_callback(device):
        nonlocal count 
        count += 1

    scanner = bleak.BleakScanner(filters={"RSSI":500})
    scanner.register_detection_callback(detection_callback)
    await scanner.start()
    await asyncio.sleep(5.0)
    await scanner.stop()
    devices = await scanner.get_discovered_devices()

    assert count == 0


# TODO: Add pathloss test