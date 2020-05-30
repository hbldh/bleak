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

@pytest.mark.async_timeout(60)
async def test_with(discover):
    async with bleak.BleakClient(discover) as client:
        assert await client.is_connected()
        value = await client.read_gatt_char("1d93b2f8-9239-11ea-bb37-0242ac130002") 
        assert value == bytearray(b'0123456789')

    # Out of scope.  Should have disconnected 
    assert False == await client.is_connected() 
