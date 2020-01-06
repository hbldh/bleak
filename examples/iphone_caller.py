import asyncio
import logging
import platform

from bleak import BleakClient

example = """
[Service] 00001800-0000-1000-8000-00805f9b34fb: Generic Access Profile
	[Characteristic] 00002a00-0000-1000-8000-00805f9b34fb: (read) | Name: , Value: b'iPhone' 
	[Characteristic] 00002a01-0000-1000-8000-00805f9b34fb: (read) | Name: , Value: b'@\x00' 
[Service] 00001801-0000-1000-8000-00805f9b34fb: Generic Attribute Profile
	[Characteristic] 00002a05-0000-1000-8000-00805f9b34fb: (indicate) | Name: , Value: None 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 9) | Value: b'\x02\x00' 
[Service] d0611e78-bbb4-4591-a5f8-487910ae4366: Unknown
	[Characteristic] 8667556c-9a37-4c91-84ed-54ee27d90049: (write,notify,extended-properties,reliable-writes) | Name: , Value: None 
		[Descriptor] 00002900-0000-1000-8000-00805f9b34fb: (Handle: 13) | Value: b'\x01\x00' 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 14) | Value: b'\x00\x00' 
[Service] 9fa480e0-4967-4542-9390-d343dc5d04ae: Unknown
	[Characteristic] af0badb1-5b99-43cd-917a-a77bc549e3cc: (write,notify,extended-properties,reliable-writes) | Name: , Value: None 
		[Descriptor] 00002900-0000-1000-8000-00805f9b34fb: (Handle: 18) | Value: b'\x01\x00' 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 19) | Value: b'\x00\x00' 
[Service] 0000180f-0000-1000-8000-00805f9b34fb: Battery Service
	[Characteristic] 00002a19-0000-1000-8000-00805f9b34fb: (read,notify) | Name: , Value: b'Could not read characteristic value for 00002a19-0000-1000-8000-00805f9b34fb: 2' 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 23) | Value: b'\x00\x00' 
[Service] 00001805-0000-1000-8000-00805f9b34fb: Current Time Service
	[Characteristic] 00002a2b-0000-1000-8000-00805f9b34fb: (read,notify) | Name: , Value: b'Could not read characteristic value for 00002a2b-0000-1000-8000-00805f9b34fb: 2' 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 27) | Value: b'\x00\x00' 
	[Characteristic] 00002a0f-0000-1000-8000-00805f9b34fb: (read) | Name: , Value: b'Could not read characteristic value for 00002a0f-0000-1000-8000-00805f9b34fb: 2' 
[Service] 0000180a-0000-1000-8000-00805f9b34fb: Device Information
	[Characteristic] 00002a29-0000-1000-8000-00805f9b34fb: (read) | Name: , Value: b'Apple Inc.' 
	[Characteristic] 00002a24-0000-1000-8000-00805f9b34fb: (read) | Name: , Value: b'iPhone10,5' 
[Service] 7905f431-b5ce-4e99-a40f-4b1e122d00d0: Unknown
	[Characteristic] 69d1d8f3-45e1-49a8-9821-9bbdfdaad9d9: (write,extended-properties,reliable-writes) | Name: , Value: None 
		[Descriptor] 00002900-0000-1000-8000-00805f9b34fb: (Handle: 38) | Value: b'\x01\x00' 
	[Characteristic] 9fbf120d-6301-42d9-8c58-25e699a21dbd: (notify) | Name: , Value: None 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 41) | Value: b'\x00\x00' 
	[Characteristic] 22eac6e9-24d6-4bb5-be44-b36ace7c7bfb: (notify) | Name: , Value: None 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 44) | Value: b'\x00\x00' 
[Service] 89d3502b-0f36-433a-8ef4-c502ad55f8dc: Unknown
	[Characteristic] 9b3c81d8-57b1-4a8a-b8df-0e56f7ca51c2: (write,notify,extended-properties,reliable-writes) | Name: , Value: None 
		[Descriptor] 00002900-0000-1000-8000-00805f9b34fb: (Handle: 48) | Value: b'\x01\x00' 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 49) | Value: b'\x00\x00' 
	[Characteristic] 2f7cabce-808d-411f-9a0c-bb92ba96c102: (write,notify,extended-properties,reliable-writes) | Name: , Value: None 
		[Descriptor] 00002900-0000-1000-8000-00805f9b34fb: (Handle: 52) | Value: b'\x01\x00' 
		[Descriptor] 00002902-0000-1000-8000-00805f9b34fb: (Handle: 53) | Value: b'\x00\x00' 
	[Characteristic] c6b2f38c-23ab-46d8-a6ab-a3a870bbd5d7: (read,write,extended-properties,reliable-writes) | Name: , Value: b'Could not read characteristic value for c6b2f38c-23ab-46d8-a6ab-a3a870bbd5d7: 2' 
		[Descriptor] 00002900-0000-1000-8000-00805f9b34fb: (Handle: 56) | Value: b'\x01\x00'

"""

async def run(address, loop, debug=False):
    log = logging.getLogger(__name__)
    if debug:
        import sys

        loop.set_debug(True)
        log.setLevel(logging.DEBUG)
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.DEBUG)
        log.addHandler(h)

    async with BleakClient(address, loop=loop) as client:
        x = await client.is_connected()
        log.info("Connected: {0}".format(x))

        for service in client.services:
            log.info("[Service] {0}: {1}".format(service.uuid, service.description))
            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = bytes(await client.read_gatt_char(char.uuid))
                    except Exception as e:
                        value = str(e).encode()
                else:
                    value = None
                log.info(
                    "\t[Characteristic] {0}: ({1}) | Name: {2}, Value: {3} ".format(
                        char.uuid, ",".join(char.properties), char.description, value
                    )
                )
                for descriptor in char.descriptors:
                    value = await client.read_gatt_descriptor(descriptor.handle)
                    log.info(
                        "\t\t[Descriptor] {0}: (Handle: {1}) | Value: {2} ".format(
                            descriptor.uuid, descriptor.handle, bytes(value)
                        )
                    )


if __name__ == "__main__":
    address = (
        #"24:71:89:cc:09:05"
        "7A:D2:14:6F:5F:5C"
        if platform.system() != "Darwin"
        else "243E23AE-4A99-406C-B317-18F1BD7B4CBE"
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(address, loop, True))
