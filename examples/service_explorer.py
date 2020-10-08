"""
Service Explorer
----------------

An example showing how to access and print out the services, characteristics and
descriptors of a connected GATT server.

Created on 2019-03-25 by hbldh <henrik.blidh@nedomkull.com>

"""
import platform
import asyncio
import logging

from bleak import BleakClient


async def run(address, debug=False):
    log = logging.getLogger(__name__)
    if debug:
        import sys

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(name)s] [%(threadName)s] [%(levelname)s] %(message)s",
            handlers=[handler],
        )
        log = logging.getLogger(__name__)
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)

    async with BleakClient(address) as client:
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
                    "\t[Characteristic] {0}: (Handle: {1}) ({2}) | Name: {3}, Value: {4} ".format(
                        char.uuid,
                        char.handle,
                        ",".join(char.properties),
                        char.description,
                        value,
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
        "24:71:89:cc:09:05"
        if platform.system() != "Darwin"
        else "15A43D03-7ACE-4826-AEC7-ADF2001A5C9B"
    )
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    loop.run_until_complete(run(address, True))
