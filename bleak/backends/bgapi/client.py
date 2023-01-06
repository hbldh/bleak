
import asyncio
import logging
import struct
from typing import Optional, Union
import uuid
import warnings

import bgapi

from ..characteristic import BleakGATTCharacteristic
from ..client import BaseBleakClient, NotifyCallback
from ..device import BLEDevice
from ..service import BleakGATTServiceCollection

from .characteristic import BleakGATTCharacteristicBGAPI, PartialCharacteristic
from .descriptor import BleakGATTDescriptorBGAPI, PartialDescriptor
from .service import BleakGATTServiceBGAPI

logger = logging.getLogger(__name__)


def _bgapi_uuid_to_str(uuid_bytes):
    """
    Converts a 16/32/128bit bytes uuid in BGAPI result format into
    the "normal" bleak string form.
    """
    if len(uuid_bytes) == 2:
        uu, = struct.unpack("<H", uuid_bytes)
        return f"0000{uu:04x}-0000-1000-8000-00805f9b34fb"
    elif len(uuid_bytes) == 4:
        uu, = struct.unpack("<L", uuid_bytes)
        return f"{uu:08x}-0000-1000-8000-00805f9b34fb"
    elif len(uuid_bytes) == 16:
        return f"{uuid.UUID(bytes=bytes(reversed(uuid_bytes)))}"
    else:
        # let's see, will BGAPI give us zero here sometimes? *fingers crossed*
        raise RuntimeError("Illegal uuid data size?!")


class BleakClientBGAPI(BaseBleakClient):
    """
    A client built to talk to a Silicon Labs "BGAPI" NCP device.
    """

    def __init__(self, address_or_ble_device: Union[BLEDevice, str], **kwargs):
        super(BleakClientBGAPI, self).__init__(address_or_ble_device, **kwargs)

        self._device = None
        if isinstance(address_or_ble_device, BLEDevice):
            self._device = address_or_ble_device

        self._loop = asyncio.get_running_loop()
        self._ch: Optional[int] = None
        # used to override mtu_size property
        self._mtu_size: Optional[int] = None
        self._services_resolved = False

        self._adapter: Optional[str] = kwargs.get("adapter", kwargs.get("ncp"))
        self._bgapi = kwargs.get("bgapi", "/home/karlp/SimplicityStudio/SDKs/gecko_sdk_2/protocol/bluetooth/api/sl_bt.xapi")
        ### XXX are we in trouble here making a new serial connection? the scanner does too!
        self._lib = bgapi.BGLib(bgapi.SerialConnector(self._adapter), self._bgapi, event_handler=self._bgapi_evt_handler)
        self._ev_connect = asyncio.Event()
        self._ev_gatt_op = asyncio.Event()
        self._buffer_characteristics = []
        self._buffer_descriptors = []

    async def connect(self, **kwargs) -> bool:
        self._lib.open()  # this starts a new thread, remember that!
        # XXX make this more reliable? if it fails hello, try again, try reset?
        self._lib.bt.system.hello()
        # Can't / shouldn't do a reset here?!  I wish the serial layer was more robust! (are we just not cleaning up after ourselves well enough?

        # TODO - move this elsewhere? we like it now for tracking adapters, but bleak has no real concept of that.
        _, self._our_address, self._our_address_type = self._lib.bt.system.get_identity_address()
        logger.info("Our Bluetooth %s address: %s", "static random" if self._our_address_type else "public device", self._our_address)

        phy = self._lib.bt.gap.PHY_PHY_1M  # XXX: some people _may_ wish to specify this. (can't use PHY_ANY!)
        atype = self._lib.bt.gap.ADDRESS_TYPE_PUBLIC_ADDRESS
        if self._device:
            # FIXME - we have the address type information in the scanner, make sure it gets here?
            pass
        _, self._ch = self._lib.bt.connection.open(self.address, atype, phy)

        async def waiter():
            await self._ev_connect.wait()

        try:
            await asyncio.wait_for(waiter(), timeout=self._timeout)
        except asyncio.exceptions.TimeoutError:
            logger.warning("Timed out attempting connection to %s", self.address)
            # FIXME - what's the "correct" exception to raise here?
            raise

        # nominally, you don't need to do this, but it's how bleak behaves, so just do it,
        # even though it's "wasteful" to enumerate everything.  It's predictable behaviour
        await self.get_services()

        return True

    async def disconnect(self) -> bool:
        logger.debug("attempting to disconnect")
        if self._ch is not None:
            self._lib.bt.connection.close(self._ch)
        self._ch = None
        self._lib.close()
        return True

    def _bgapi_evt_handler(self, evt):
        """
        THIS RUNS IN THE BGLIB THREAD!
        and because of this, we can't call commands from here ourself,
        remember to use _loop.call_soon_threadsafe....
        """
        if evt == "bt_evt_system_boot":
            logger.debug("NCP booted: %d.%d.%db%d hw:%d hash: %x", evt.major, evt.minor, evt.patch, evt.build, evt.hw, evt.hash)
            # We probably don't want to do anything else here?!
        elif evt == "bt_evt_connection_opened":
            # Right? right?!
            assert(self._ch == evt.connection)
            # do this on the right thread!
            self._loop.call_soon_threadsafe(self._ev_connect.set)
        elif evt == "bt_evt_connection_closed":
            logger.debug("Disconnected conn: %d: reason: %d (%#x)", evt.connection, evt.reason, evt.reason)
            self._loop.call_soon_threadsafe(self._disconnected_callback, self)
            self._ch = None
        elif (
            evt == "bt_evt_connection_parameters"
            or evt == "bt_evt_connection_phy_status"
            or evt == "bt_evt_connection_remote_used_features"
        ):
            logger.debug("ignoring 'extra' info in: %s", evt)
            # We don't need anything else here? just confirmations, and avoid "unhandled" warnings?
        elif evt == "bt_evt_gatt_mtu_exchanged":
            self._mtu_size = evt.mtu
        elif evt == "bt_evt_gatt_service":
            uus = _bgapi_uuid_to_str(evt.uuid)
            service = BleakGATTServiceBGAPI(dict(uuid=uus, handle=evt.service))
            self._loop.call_soon_threadsafe(self.services.add_service, service)
        elif evt == "bt_evt_gatt_characteristic":
            uus = _bgapi_uuid_to_str(evt.uuid)
            # Unlike with services, we don't have enough information to directly create the BleakCharacteristic here.
            self._loop.call_soon_threadsafe(self._buffer_characteristics.append, PartialCharacteristic(uuid=uus, handle=evt.characteristic, properties=evt.properties))
        elif evt == "bt_evt_gatt_descriptor":
            uus = _bgapi_uuid_to_str(evt.uuid)
            # Unlike with services, we don't have enough information to directly create the BleakDescriptor here.
            self._loop.call_soon_threadsafe(self._buffer_descriptors.append, PartialDescriptor(uuid=uus, handle=evt.descriptor))
        elif evt == "bt_evt_gatt_procedure_completed":
            self._loop.call_soon_threadsafe(self._ev_gatt_op.set)
        else:
            # Loudly show all the places we're not handling things yet!
            logger.warning(f"unhandled bgapi evt! {evt}")

    @property
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection"""
        if self._mtu_size is None:
            warnings.warn(
                "Using default MTU value. Call _acquire_mtu() or set _mtu_size first to avoid this warning."
            )
            return 23

        return self._mtu_size

    async def pair(self, *args, **kwargs) -> bool:
        raise NotImplementedError

    async def unpair(self) -> bool:
        raise NotImplementedError

    @property
    def is_connected(self) -> bool:
        return self._ch is not None

    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        if self._services_resolved:
            return self.services

        self._ev_gatt_op.clear()
        self._lib.bt.gatt.discover_primary_services(self._ch)
        await self._ev_gatt_op.wait()

        for s in self.services:
            self._ev_gatt_op.clear()
            self._buffer_characteristics.clear()
            self._lib.bt.gatt.discover_characteristics(self._ch, s.handle)
            await self._ev_gatt_op.wait()

            # ok, we've now got a stack of partial characteristics
            for pc in self._buffer_characteristics:
                bc = BleakGATTCharacteristicBGAPI(pc, s.uuid, s.handle, self.mtu_size - 3)
                self.services.add_characteristic(bc)  # Add to the root collection!

                # Now also get the descriptors
                self._ev_gatt_op.clear()
                self._buffer_descriptors.clear()
                self._lib.bt.gatt.discover_descriptors(self._ch, bc.handle)
                await self._ev_gatt_op.wait()
                for pd in self._buffer_descriptors:
                    bd = BleakGATTDescriptorBGAPI(pd, bc.uuid, bc.handle)
                    self.services.add_descriptor(bd)  # Add to the root collection!

        self._services_resolved = True
        return self.services

    async def read_gatt_char(self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
                             **kwargs) -> bytearray:
        raise NotImplementedError

    async def read_gatt_descriptor(self, handle: int, **kwargs) -> bytearray:
        raise NotImplementedError

    async def write_gatt_char(self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
                              data: Union[bytes, bytearray, memoryview], response: bool = False) -> None:
        raise NotImplementedError

    async def write_gatt_descriptor(self, handle: int, data: Union[bytes, bytearray, memoryview]) -> None:
        raise NotImplementedError

    async def start_notify(self, characteristic: BleakGATTCharacteristic, callback: NotifyCallback, **kwargs) -> None:
        raise NotImplementedError

    async def stop_notify(self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID]) -> None:
        raise NotImplementedError



