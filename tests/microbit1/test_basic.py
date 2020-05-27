
# Python: Requires alt-pytest-asyncio  (timeouts and asynchio)
# Micro:bit:  Be sure they are running a recent version of firmware (0253 or later)
#       https://microbit.org/get-started/user-guide/firmware/


#  pytest  file.py::test     
#    -o log_cli=true     to log all messages
# pytest test_basic.py::test_short_writes_resp4 -o log_cli=true


import asyncio
import pytest
from common_fixtures import *

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
    numServices = 0
    for s in client.services:
        assert s.uuid.lower() in ['180a', '1d93af38-9239-11ea-bb37-0242ac130002']
        numServices = numServices + 1
    assert numServices == 2

@pytest.mark.async_timeout(30)
async def test_short_read(client):
    # Single, short packet
    value = await client.read_gatt_char("1d93b2f8-9239-11ea-bb37-0242ac130002") 
    assert value == bytearray(b'0123456789')

@pytest.mark.async_timeout(30)
async def test_packet_read(client):
    # Single packet that uses all available bytes
    value = await client.read_gatt_char("1d93b488-9239-11ea-bb37-0242ac130002") 
    assert value == bytearray(b'abcdefghijklmnopqrst')

@pytest.mark.async_timeout(30)
async def test_long_read(client):
    # Requires multiple packets
    value = await client.read_gatt_char("1d93b56e-9239-11ea-bb37-0242ac130002") 
    assert value == bytearray(b'abcdefghijklmnopqrstuvwzyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

@pytest.mark.async_timeout(60)
async def test_short_writes_noResp1(client):
    # Short write without response (then read back to confirm)
    char = "1d93b636-9239-11ea-bb37-0242ac130002"

    toSend = bytearray(B'ABCDEF')
    await client.write_gatt_char(char, toSend)
    value = await client.read_gatt_char(char) 
    assert value == toSend
    


@pytest.mark.async_timeout(60)
async def test_short_writes_noResp2(client):
    # Short write without response (then read back to confirm)
    char = "1d93b636-9239-11ea-bb37-0242ac130002"

    toSend = bytearray(B'GHIJKL')
    await client.write_gatt_char(char, toSend)
    value = await client.read_gatt_char(char) 
    assert value == toSend


@pytest.mark.async_timeout(60)
async def test_short_writes_noResp3(client):
    # Write a full 20 bytes / packet
    char = "1d93b636-9239-11ea-bb37-0242ac130002"

    toSend = bytearray(B'abcdefghijklmnopqrst')
    await client.write_gatt_char(char, toSend)
    value = await client.read_gatt_char(char) 
    assert value == toSend


@pytest.mark.async_timeout(60)
async def test_short_writes_resp1(client):
    # Write w/ response short
    char = "1d93b942-9239-11ea-bb37-0242ac130002"

    toSend = bytearray(B'abcdef')
    await client.write_gatt_char(char, toSend, response=True)
    value = await client.read_gatt_char(char) 
    assert value == toSend

@pytest.mark.async_timeout(60)
async def test_short_writes_resp2(client):
    # Write w/ response full packet
    char = "1d93b942-9239-11ea-bb37-0242ac130002"

    toSend = bytearray(B'01234567890123456789')
    await client.write_gatt_char(char, toSend, response=True)
    value = await client.read_gatt_char(char) 
    assert value == toSend

@pytest.mark.async_timeout(60)
async def test_short_writes_resp3(client):
    # Write w/ response more than one packet
    char = "1d93b942-9239-11ea-bb37-0242ac130002"

    toSend = bytearray(B'abcdefghijklmnopqrstuvwxyz')
    await client.write_gatt_char(char, toSend, response=True)
    value = await client.read_gatt_char(char) 
    assert value == toSend


@pytest.mark.async_timeout(60)
async def test_short_writes_resp4(client):
    # Write w/ response 80 bytes (max size)
    char = "1d93b942-9239-11ea-bb37-0242ac130002"

    toSend = bytearray(B'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()<>:"{}/?')
    await client.write_gatt_char(char, toSend, response=True)
    value = await client.read_gatt_char(char) 
    assert value == toSend


# @pytest.mark.skip(reason="Fails on OSX / Python error")
@pytest.mark.async_timeout(60)
async def test_short_writes_resp4(client):
    # Write w/ response 81 bytes (OVER max size)
    char = "1d93b942-9239-11ea-bb37-0242ac130002"

    small = bytearray(B'data')
    await client.write_gatt_char(char, small, response=True)
    value = await client.read_gatt_char(char) 
    assert value == small


    toSend = bytearray(B'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()<>:"{}/?E')
    # Write should fail / raise exception
    with pytest.raises(bleak.BleakError) as error:
        await client.write_gatt_char(char, toSend, response=True)
    # Value should be unchanged 
    await asyncio.sleep(0.5)
    value = await client.read_gatt_char(char) 
    assert value == small


# Test notification

# Test indication


# Test the "with" structure

# Test the disconnect callback