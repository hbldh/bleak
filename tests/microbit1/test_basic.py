
# Requires pytest-asyncio


import os
import platform
import time

import asyncio
import pytest

# import pytest-asyncio
from shutil import copyfile



import sys
sys.path.insert(1, '../..')  # Use local bleak
# Only for local testing (not on cloud)
import logging
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

# import bleak
logger = logging.getLogger(__name__)
logger.warning("Importing Bleak")
from bleak import discover
logger.warning("DONE Importing Bleak")


microbit_volume = ''
"""Setup locations for OS"""
if platform.system() == "Linux":
    raise Exception('Not implemented for Linux yet')
elif platform.system() == "Windows":
    raise Exception('Not implemented for Windows yet')
elif platform.system() == "Darwin":
    microbit_volume = '/Volumes/MICROBIT/'


def waitForMicrobitVolume():
    while not os.path.isdir(microbit_volume):
        print(f'Waiting for micro:bit to become available at {microbit_volume}')
        time.sleep(1)
    print("microbit available")


def update_firmware(file: str):
    """
    Update Micro:bit firmware to specific version.
    file should refer to a .hex file in the ./firmware directory
    relies on global microbit_volume to be cnofigured
    """
    waitForMicrobitVolume()
    # Copy firmware to drive 
    copyfile("./firmware/"+file, microbit_volume+file)
    # Will this work on all oses?
    print(f'Waiting for micro:bit to restart / unmount')
    while os.path.isdir(microbit_volume):
        # TODO: Replace with await asyncio.sleep(20)  # Sleep 20ms
        pass
    waitForMicrobitVolume()
    print("Microbit ready for testing")


@pytest.fixture()   # scope="session"  # Confirm this???
def configure_firmware():
    update_firmware('testservice.hex')

# @pytest.mark.asyncio
@pytest.mark.async_timeout(20)
async def test_discover():
    devices = await discover(filters={"UUIDs":["1d93af38-9239-11ea-bb37-0242ac130002"]})
    if len(devices) == 0:
        pytest.exit('No device found.  Confirm that device is powered and filtering by UUID works')
    assert True
