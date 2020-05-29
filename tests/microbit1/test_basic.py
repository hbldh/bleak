
# Python: Requires alt-pytest-asyncio  (timeouts and asynchio)
# Micro:bit:  Be sure they are running a recent version of firmware (0253 or later)
#       https://microbit.org/get-started/user-guide/firmware/


#  pytest  file.py::test     
#    -o log_cli=true     to log all messages
# pytest test_basic.py::test_short_writes_resp4 -o log_cli=true


# TODO: 
#
#  These all need a lot of cleanup and decoupling, but they are a good start on proof-of-concept. 
#  After adding a few more features and corresponding tests it's time for cleanup.
# 
#  Probably worth while to separate into more files.

#  More tests to add:
#      Test the "with" structure and ensuring disconnect (and memory???)
#      Test scanning behavior and filtering 
#      Test multiple services/characteristics with the same UUID
#
#
#  General cleanup and improvements for multiple platforms and to avoid conflicts with CI?
#
#

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



@pytest.mark.async_timeout(60)
async def test_single_notification(client):
    # Write w/ response more than one packet
    last_value = None
    # Setup callback
    def callback(sender, data):
        nonlocal last_value
        last_value = data

    await client.start_notify("1d93bb2c-9239-11ea-bb37-0242ac130002", callback)
    # Reset counter and set period to 0.5s (500ms between notifies)
    await client.write_gatt_char("1d93b6fe-9239-11ea-bb37-0242ac130002", 
                                    bytearray( (500).to_bytes(4, byteorder='little') ), 
                                    response=True)

    start_time = time()
    await asyncio.sleep(4.1)
    await client.stop_notify("1d93bb2c-9239-11ea-bb37-0242ac130002")
    stop_time = time()

    stop = int.from_bytes(last_value, byteorder="little", signed=False)

    expected = floor((stop_time-start_time)*2)  # 2x per second

    print(f"stop: {stop}  expected: {expected}")
    assert stop >= expected-1 and stop <= expected+1



@pytest.mark.async_timeout(60)
async def test_two_notifications(client):
    # Write w/ response more than one packet
    last_value1 = None
    update_count1 = 0
    # Setup callback
    def callback1(sender, data):
        nonlocal last_value1
        last_value1 = data
        nonlocal update_count1
        update_count1 += 1
    await client.start_notify("1d93bb2c-9239-11ea-bb37-0242ac130002", callback1)

    start_time1 = time()

    last_value2 = None
    update_count2 = 0
    # Setup callback
    def callback2(sender, data):
        nonlocal last_value2
        last_value2 = data
        nonlocal update_count2
        update_count2 += 1
    await client.start_notify("1d93bc9e-9239-11ea-bb37-0242ac130002", callback2)

    # Reset counter1 and set period to 0.5s (500ms between notifies)
    await client.write_gatt_char("1d93b6fe-9239-11ea-bb37-0242ac130002", 
                                    bytearray( (500).to_bytes(4, byteorder='little') ), 
                                    response=True)

    # Reset counter2 and set period to 1s (1000ms between notifies)
    await client.write_gatt_char("1d93bbea-9239-11ea-bb37-0242ac130002", 
                                    bytearray( (1000).to_bytes(4, byteorder='little') ), 
                                    response=True)

    start_time = time()
    await asyncio.sleep(7.1)
    await client.stop_notify("1d93bb2c-9239-11ea-bb37-0242ac130002")
    await client.stop_notify("1d93bc9e-9239-11ea-bb37-0242ac130002")
    stop_time = time()

    stop1 = int.from_bytes(last_value1, byteorder="little", signed=False)
    stop2 = int.from_bytes(last_value2, byteorder="little", signed=False)

    expected1 = floor((stop_time-start_time)*2)  # 2x per second
    expected2 = floor((stop_time-start_time))  # 1x per second

    print(f"stop: {stop1}  expected: {expected1}")
    assert stop1 >= expected1-1 and stop1 <= expected1+1
    print(f"stop: {stop2}  expected: {expected2}")
    assert stop2 >= expected2-1 and stop2 <= expected2+1
    assert update_count1 >= expected1-1 and update_count1 <= expected1+1
    assert update_count2 >= expected2-1 and update_count2 <= expected2+1



@pytest.mark.async_timeout(60)
async def test_single_indication(client):
    # Write w/ response more than one packet
    last_value = None
    # Setup callback
    def callback(sender, data):
        nonlocal last_value
        last_value = data

    await client.start_notify("1d93be06-9239-11ea-bb37-0242ac130002", callback)
    # Reset counter and set period to 0.5s (500ms between notifies)
    await client.write_gatt_char("1d93bd52-9239-11ea-bb37-0242ac130002", 
                                    bytearray( (500).to_bytes(4, byteorder='little') ), 
                                    response=True)

    start_time = time()
    await asyncio.sleep(4.1)
    await client.stop_notify("1d93be06-9239-11ea-bb37-0242ac130002")
    stop_time = time()

    stop = int.from_bytes(last_value, byteorder="little", signed=False)

    expected = floor((stop_time-start_time)*2)  # 2x per second

    assert stop >= expected-1 and stop <= expected+1



@pytest.mark.async_timeout(60)
async def test_two_indications(client):
    # Write w/ response more than one packet
    last_value1 = None
    update_count1 = 0
    # Setup callback
    def callback1(sender, data):
        nonlocal last_value1
        last_value1 = data
        nonlocal update_count1
        update_count1 += 1
    await client.start_notify("1d93be06-9239-11ea-bb37-0242ac130002", callback1)

    start_time1 = time()

    last_value2 = None
    update_count2 = 0
    # Setup callback
    def callback2(sender, data):
        nonlocal last_value2
        last_value2 = data
        nonlocal update_count2
        update_count2 += 1
    await client.start_notify("1d93bf82-9239-11ea-bb37-0242ac130002", callback2)

    # Reset counter1 and set period to 0.5s (500ms between notifies)
    await client.write_gatt_char("1d93bd52-9239-11ea-bb37-0242ac130002", 
                                    bytearray( (500).to_bytes(4, byteorder='little') ), 
                                    response=True)

    start_time = time()

    # Reset counter2 and set period to 1s (1000ms between notifies)
    await client.write_gatt_char("1d93bec4-9239-11ea-bb37-0242ac130002", 
                                    bytearray( (1000).to_bytes(4, byteorder='little') ), 
                                    response=True)

    await asyncio.sleep(7.1)
    await client.stop_notify("1d93be06-9239-11ea-bb37-0242ac130002")
    await client.stop_notify("1d93bf82-9239-11ea-bb37-0242ac130002")
    stop_time = time()

    stop1 = int.from_bytes(last_value1, byteorder="little", signed=False)
    stop2 = int.from_bytes(last_value2, byteorder="little", signed=False)

    expected1 = floor((stop_time-start_time)*2)  # 2x per second
    expected2 = floor((stop_time-start_time))  # 1x per second

    assert stop1 >= expected1-1 and stop1 <= expected1+1
    assert stop2 >= expected2-1 and stop2 <= expected2+1
    assert update_count1 >= expected1-1 and update_count1 <= expected1+1
    assert update_count2 >= expected2-1 and update_count2 <= expected2+1



@pytest.mark.async_timeout(60)
async def test_readwrite_user_desc_descriptor(client):
    descs = [(h,d) for (h, d) in client.services.descriptors.items() if d.characteristic_uuid == "1d93c432-9239-11ea-bb37-0242ac130002".upper()]
    assert len(descs) == 5
    uuidsToHandles = { d.uuid:h for (h,d) in descs}

    # extProp = "2900"
    # userDesc = "2901"
    # serverConfig = "2903"
    # misc = "2929"
    # # 2900, 2901, 2903, 2904, and 2929 
    await client.write_gatt_descriptor(uuidsToHandles["2901"], bytearray(b'Change 1'))
    userDesc = await client.read_gatt_descriptor(uuidsToHandles["2901"])
    assert userDesc == bytearray(b"Change 1")
    await client.write_gatt_descriptor(uuidsToHandles["2901"], bytearray(b'Change 2'))
    userDesc = await client.read_gatt_descriptor(uuidsToHandles["2901"])
    assert userDesc == bytearray(b"Change 2")

@pytest.mark.async_timeout(60)
async def test_read_descriptors(client):
    descs = [(h,d) for (h, d) in client.services.descriptors.items() if d.characteristic_uuid == "1d93c432-9239-11ea-bb37-0242ac130002".upper()]
    assert len(descs) == 5
    uuidsToHandles = { d.uuid:h for (h,d) in descs}

    extProp = await client.read_gatt_descriptor(uuidsToHandles["2900"])
    assert extProp == bytearray( (2).to_bytes(2, byteorder="little") )

    serverConfig = await client.read_gatt_descriptor(uuidsToHandles["2903"])
    assert serverConfig == bytearray( (0).to_bytes(2, byteorder="little") )

    misc = await client.read_gatt_descriptor(uuidsToHandles["2929"])
    assert misc == bytearray((0).to_bytes(2, byteorder="little") )  # 7 bytes 

    presFmt = await client.read_gatt_descriptor(uuidsToHandles["2904"])
    assert presFmt ==  bytearray( [0x0e, 0x03, 0x10, 0x27, 0x01, 0x00, 0x00] )


@pytest.mark.async_timeout(60)
async def test_authorized_read_write(client):
    # Read and write to a characteristic that is authorized 

    # Set it to "authorized" by writting to permission characteristic
    await client.write_gatt_char("1d93b7c6-9239-11ea-bb37-0242ac130002", 
                                    bytearray( b'RW' ), 
                                    response=True)



    # Write to the characteristic that requires authorization
    await client.write_gatt_char("1d93b884-9239-11ea-bb37-0242ac130002", 
                                    bytearray( b'012345' ), 
                                    response=True)
    # Verify with a read
    value = await client.read_gatt_char("1d93b884-9239-11ea-bb37-0242ac130002") 
    assert value == bytearray(b'012345')

    # Write to the characteristic that requires authorization
    await client.write_gatt_char("1d93b884-9239-11ea-bb37-0242ac130002", 
                                    bytearray( b'ABCDEF' ), 
                                    response=True)
    # Verify with a read
    value = await client.read_gatt_char("1d93b884-9239-11ea-bb37-0242ac130002") 
    assert value == bytearray(b'ABCDEF')


@pytest.mark.async_timeout(60)
async def test_unauthorized_read_write(client):
    # Read and write to a characteristic that is authorized 

    # Set it to "NOT authorized" by writting to permission characteristic
    logger.debug("Setting Permissions...")
    await client.write_gatt_char("1d93b7c6-9239-11ea-bb37-0242ac130002", 
                                    bytearray( b'Nope' ), 
                                    response=True)

    logger.debug("Trying Write")
    # Write to the characteristic that requires authorization
    with pytest.raises(bleak.BleakError) as error:
        await client.write_gatt_char("1d93b884-9239-11ea-bb37-0242ac130002", 
                                        bytearray( b'012345' ), 
                                        response=True)

    # # Try a read
    logger.debug("Trying Read")
    with pytest.raises(bleak.BleakError) as error:
        value = await client.read_gatt_char("1d93b884-9239-11ea-bb37-0242ac130002") 

    
    



