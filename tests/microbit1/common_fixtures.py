import os
import platform
from shutil import copyfile
import asyncio

import pytest

_IS_CI = os.environ.get("CI", "false").lower() == "true"
_IS_AZURE_PIPELINES = os.environ.get("SYSTEM_HOSTTYPE", "") == "build"

if platform.system() != "Darwin":
    _OS = os.environ.get("AGENT_OS").lower()
else:
    _OS = platform.system()

import sys
sys.path.insert(1, '../..')  # Use local bleak
# Only for local testing (not on cloud)
# import logging
# logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

# import bleak
# logger = logging.getLogger(__name__)
# logger.warning("Importing Bleak")
import bleak 


microbit_volume = ''
microbit_volume2 = ''
"""Setup locations for OS"""
if platform.system() == "Linux":
    raise Exception('Not implemented for Linux yet')
elif platform.system() == "Windows":
    raise Exception('Not implemented for Windows yet')
elif platform.system() == "Darwin":
    microbit_volume = '/Volumes/MICROBIT/'
    microbit_volume2 = '/Volumes/MICROBIT 1/'

        
async def waitForMicrobitVolume(volume=microbit_volume):
    print(f'Waiting for micro:bit to become available at {volume}')
    while not os.path.isdir(volume):
        await asyncio.sleep(0.01)
    print("microbit available")


@pytest.mark.async_timeout(30)
async def update_firmware(file: str, volume=microbit_volume):
    """
    Update Micro:bit firmware to specific version.
    file should refer to a .hex file in the ./firmware directory
    relies on global microbit_volume to be configured
    """
    await waitForMicrobitVolume(volume=volume)
    # Copy firmware to drive 
    copyfile("./firmware/"+file, volume+file)
    # Will this work on all oses?
    print(f'Waiting for micro:bit to restart / unmount')
    while os.path.isdir(volume):
        await asyncio.sleep(0.01)
    await waitForMicrobitVolume(volume=volume)
    print("Microbit ready for testing")


@pytest.fixture(scope="session")   
@pytest.mark.async_timeout(30)
async def configure_firmware(request):
    if request.config.getoption("--nofw") == False:
        await update_firmware('testservice.hex')
    return True


# Put firmware on device 2
@pytest.fixture(scope="session")   
@pytest.mark.async_timeout(30)
async def configure_firmware2(request):
    await update_firmware('testservice.hex', volume=microbit_volume2)
    return True


# Put firmware *B* on device 2
@pytest.fixture(scope="session")   
@pytest.mark.async_timeout(30)
async def configure_firmwareB2(request):
    await update_firmware('testservice_B.hex', volume=microbit_volume2)
    return True

@pytest.fixture(scope="session")
@pytest.mark.async_timeout(12)
async def discover(configure_firmware):
    # Always takes "timeout" seconds, so timeout should be less than async_timeout
    devices = await bleak.discover(filters={"UUIDs":["1d93af38-9239-11ea-bb37-0242ac130002"]}, timeout=10)
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


@pytest.fixture(scope="module")  
@pytest.mark.async_timeout(60)
async def client(discover, request):
    # Connect to the discovered device

    assert discover!=None

    client = bleak.BleakClient(discover)
    await client.connect(timeout=5)
    def disconnect():       
        loop = asyncio.get_event_loop()
        future = loop.create_task(client.disconnect())
        loop.run_until_complete(future)
    request.addfinalizer(disconnect)
    return client
