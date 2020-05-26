
# Python: Requires alt-pytest-asyncio  (timeouts and asynchio)
# Micro:bit:  Be sure they are running a recent version of firmware (0253 or later)
#       https://microbit.org/get-started/user-guide/firmware/

import os
import platform
import time

import asyncio
import pytest

from shutil import copyfile
# from time import time  # For timeouts


import sys
sys.path.insert(1, '../..')  # Use local bleak
# Only for local testing (not on cloud)
import logging
# logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

# import bleak
# logger = logging.getLogger(__name__)
# logger.warning("Importing Bleak")
import bleak 
# logger.warning("DONE Importing Bleak")


microbit_volume = ''
"""Setup locations for OS"""
if platform.system() == "Linux":
    raise Exception('Not implemented for Linux yet')
elif platform.system() == "Windows":
    raise Exception('Not implemented for Windows yet')
elif platform.system() == "Darwin":
    microbit_volume = '/Volumes/MICROBIT/'


async def waitForMicrobitVolume():
    print(f'Waiting for micro:bit to become available at {microbit_volume}')
    while not os.path.isdir(microbit_volume):
        await asyncio.sleep(0.01)
    print("microbit available")


@pytest.mark.async_timeout(30)
async def update_firmware(file: str):
    """
    Update Micro:bit firmware to specific version.
    file should refer to a .hex file in the ./firmware directory
    relies on global microbit_volume to be cnofigured
    """
    await waitForMicrobitVolume()
    # Copy firmware to drive 
    copyfile("./firmware/"+file, microbit_volume+file)
    # Will this work on all oses?
    print(f'Waiting for micro:bit to restart / unmount')
    while os.path.isdir(microbit_volume):
        await asyncio.sleep(0.01)
    await waitForMicrobitVolume()
    print("Microbit ready for testing")





# Only needs to be done once (although re-doing it will reset state after failures)
@pytest.fixture(scope="session")   
@pytest.mark.async_timeout(30)
async def configure_firmware():
    #await update_firmware('testservice.hex')
    return True

@pytest.fixture(scope="session")
@pytest.mark.async_timeout(30)
async def discover(configure_firmware):
    # Always takes "timeout" seconds, so timeout should be less than async_timeout
    devices = await bleak.discover(filters={"UUIDs":["1d93af38-9239-11ea-bb37-0242ac130002"]}, timeout=20)
    # Make sure there's a least one device
    if len(devices) == 0:
        return None
    # Make sure all matching devices have the UUID in the metadata
    for d in devices:
        assert d.metadata != None 
        assert d.metadata['uuids'] != None 
        assert '1d93af38-9239-11ea-bb37-0242ac130002' in d.metadata['uuids']
    # Return the first device found
    return devices[0].address


@pytest.fixture(scope="session")  
@pytest.mark.async_timeout(60)
async def client(discover, request):
    # Connect to the discovered device
    print(f'Connecting to {discover}')
    client = bleak.BleakClient(discover)
    await client.connect(timeout=30)
    def disconnect():       
        loop = asyncio.get_event_loop()
        future = loop.create_task(client.disconnect())
        loop.run_until_complete(future)
    request.addfinalizer(disconnect)
    return client


### Actual Tests! ###

# Returns device address
@pytest.mark.async_timeout(30)
async def test_discover(discover):
    assert discover != None

@pytest.mark.async_timeout(30)
async def test_connect(client):
    assert client != None

@pytest.mark.async_timeout(30)
async def test_services(client):
    num = 0
    for s in client.services:
        assert s.uuid.lower() in ['180a', '1d93af38-9239-11ea-bb37-0242ac130002']
        num = num + 1
    assert num == 2

