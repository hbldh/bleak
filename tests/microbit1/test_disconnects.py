import asyncio
import pytest
from common_fixtures import *


import logging
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

### Actual Tests! ###



@pytest.mark.async_timeout(30)
async def test_disconnect_and_reconnect(client):
    if not await client.is_connected():
        client.connect()
    assert await client.is_connected()
    await client.disconnect()
    assert not await client.is_connected()
    await client.connect(timeout=10)
    assert await client.is_connected()


@pytest.mark.async_timeout(30)
async def test_disconnect_callback(client):
    if not await client.is_connected():
        client.connect()
    connected = True
    def callback(client, other):
        nonlocal connected
        connected = False
    client.set_disconnected_callback(callback)
    await client.disconnect()
    await asyncio.sleep(2)
    assert False == connected


@pytest.mark.async_timeout(30)
async def test_client_init_disconnect_and_reconnect(client):
    if not await client.is_connected():
        client.connect()
    connected = True
    def callback(client, other):
        nonlocal connected
        connected = False
    client.set_disconnected_callback(callback)

    char = "1d93c1e4-9239-11ea-bb37-0242ac130002"  # Characteristic for service (peripheral) initiated disconnect
    # Wait 1s (1000ms)
    toSend = bytearray( (1000).to_bytes(4, byteorder='little') )
    await client.write_gatt_char(char, toSend, response=True)

    await asyncio.sleep(2)
    assert False == connected

    await client.connect(timeout=10)
    assert await client.is_connected()



@pytest.mark.async_timeout(30)
async def test_client_unexpected_disconnect_and_reconnect(client):
    if not await client.is_connected():
        client.connect()
    connected = True
    def callback(client, other):
        nonlocal connected
        connected = False
    client.set_disconnected_callback(callback)

    char = "1d93c2c0-9239-11ea-bb37-0242ac130002"  # Characteristic for service (peripheral) initiated disconnect
    # Wait 1s (1000ms)
    toSend = bytearray( (1000).to_bytes(4, byteorder='little') )
    await client.write_gatt_char(char, toSend, response=True)

    await asyncio.sleep(10)  # Wait some time to get the callback
    assert False == connected

    await client.connect(timeout=20)
    assert await client.is_connected()