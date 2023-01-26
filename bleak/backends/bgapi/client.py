import os

import asyncio
import logging
import struct
from typing import Optional, Union
import uuid
import warnings


from ...exc import BleakError
from ..characteristic import BleakGATTCharacteristic, GattCharacteristicsFlags
from ..client import BaseBleakClient, NotifyCallback
from ..device import BLEDevice
from ..service import BleakGATTServiceCollection

from .characteristic import BleakGATTCharacteristicBGAPI, PartialCharacteristic
from .descriptor import BleakGATTDescriptorBGAPI, PartialDescriptor
from .service import BleakGATTServiceBGAPI

from . import BgapiRegistry


def _bgapi_uuid_to_str(uuid_bytes):
    """
    Converts a 16/32/128bit bytes uuid in BGAPI result format into
    the "normal" bleak string form.
    """
    if len(uuid_bytes) == 2:
        (uu,) = struct.unpack("<H", uuid_bytes)
        return f"0000{uu:04x}-0000-1000-8000-00805f9b34fb"
    elif len(uuid_bytes) == 4:
        (uu,) = struct.unpack("<L", uuid_bytes)
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
        tag = kwargs.get("logtag", hex(id(self)))
        self.log = logging.getLogger(f"bleak.backends.bgapi.client.{tag}")

        self._device = None
        if isinstance(address_or_ble_device, BLEDevice):
            self._device = address_or_ble_device

        self._loop = asyncio.get_running_loop()
        self._ch: Optional[int] = None
        # used to override mtu_size property
        self._mtu_size: Optional[int] = None
        self._services_resolved = False

        # Env vars have priority
        self._bgapi = os.environ.get("BLEAK_BGAPI_XAPI", kwargs.get("bgapi", None))
        if not self._bgapi:
            raise BleakError(
                "BGAPI file for your target (sl_bt.xapi) is required, normally this is in your SDK tree"
            )
        self._adapter = os.environ.get(
            "BLEAK_BGAPI_ADAPTER", kwargs.get("adapter", "/dev/ttyACM0")
        )

        self._bgh = BgapiRegistry.get(self._adapter, self._bgapi)

        self._ev_connect = asyncio.Event()
        self._ev_gatt_op = asyncio.Event()
        self._ev_disconnected = asyncio.Event()
        self._buffer_characteristics = []
        self._buffer_descriptors = []
        self._buffer_data = []
        self._cbs_notify = {}

    async def connect(self, **kwargs) -> bool:
        # TODO both of these should be ... layered differentyly?
        # XXX: some people _may_ wish to specify this. (can't use PHY_ANY!)
        phy = self._bgh.lib.bt.gap.PHY_PHY_1M
        atype = self._bgh.lib.bt.gap.ADDRESS_TYPE_PUBLIC_ADDRESS
        if self._device:
            # FIXME - we have the address type information in the scanner, make sure it gets here?
            pass
        self._ch = await self._bgh.connect(self.address, atype, phy, self._bgapi_evt_handler)
        self._ev_disconnected.clear()  # This should allow people to re-use client objects.

        try:
            # with the invoke or not?!
            await asyncio.wait_for(self._ev_connect.wait(), timeout=self._timeout)

        except asyncio.exceptions.TimeoutError:
            self.log.warning("Timed out attempting connection to %s", self.address)
            # According to the NCP API docs, we "should" request to close the connection here!
            await self.disconnect()
            # FIXME - what's the "correct" exception to raise here?
            raise

        # nominally, you don't need to do this, but it's how bleak behaves, so just do it,
        # even though it's "wasteful" to enumerate everything.  It's predictable behaviour
        # enumerating services/characteristics does a series of nested waits,
        # make sure we can handle being disconnected during that process
        d, p = await asyncio.wait([asyncio.Task(self.get_services(), name="get_services"),
                                   asyncio.Task(self._ev_disconnected.wait(), name="disconn")
                                   ],
                                  return_when=asyncio.FIRST_COMPLETED)
        [t.cancel() for t in p]  # cleanup and avoid "Task was destroyed but it is pending"
        if self._ev_disconnected.is_set():
            return False

        return True

    async def disconnect(self) -> bool:
        if self._ch is not None:
            await self._bgh.disconnect(self._ch)
        else:
            # This happens when the remote side disconnects us
            pass
        self._ch = None
        return True

    def _bgapi_evt_handler(self, evt):
        """
        THIS RUNS IN THE BGLIB THREAD!
        and because of this, we can't call commands from here ourself,
        remember to use _loop.call_soon_threadsafe....
        """
        if evt == "bt_evt_connection_opened":
            # The internal handler should ensure this
            assert self._ch == evt.connection
            # do this on the right thread!
            self._loop.call_soon_threadsafe(self._ev_connect.set)
        elif evt == "bt_evt_connection_closed":
            self.log.info(
                "Disconnected connection: %d: reason: %d (%#x)",
                evt.connection,
                evt.reason,
                evt.reason,
            )
            if self._disconnected_callback:
                self._loop.call_soon_threadsafe(self._disconnected_callback, self)
            self._loop.call_soon_threadsafe(self._ev_disconnected.set)
            # the conn handle is _dead_ now. if you try and keep using this, you'll get command errors
            self._ch = None
        elif (
            evt == "bt_evt_connection_parameters"
            or evt == "bt_evt_connection_phy_status"
            or evt == "bt_evt_connection_remote_used_features"
            or evt == "bt_evt_connection_tx_power"
        ):
            #self.log.debug("ignoring 'extra' info in: %s", evt)
            # We don't need anything else here? just confirmations, and avoid "unhandled" warnings?
            pass
        elif evt == "bt_evt_gatt_mtu_exchanged":
            self._mtu_size = evt.mtu
        elif evt == "bt_evt_gatt_service":
            uus = _bgapi_uuid_to_str(evt.uuid)
            service = BleakGATTServiceBGAPI(dict(uuid=uus, handle=evt.service))
            self._loop.call_soon_threadsafe(self.services.add_service, service)
        elif evt == "bt_evt_gatt_characteristic":
            uus = _bgapi_uuid_to_str(evt.uuid)
            # Unlike with services, we don't have enough information to directly create the BleakCharacteristic here.
            self._loop.call_soon_threadsafe(
                self._buffer_characteristics.append,
                PartialCharacteristic(
                    uuid=uus, handle=evt.characteristic, properties=evt.properties
                ),
            )
        elif evt == "bt_evt_gatt_characteristic_value":
            # This handles reads, long reads, and notifications/indications
            if self._cbs_notify.get(evt.characteristic, False):
                self._loop.call_soon_threadsafe(
                    self._cbs_notify[evt.characteristic], evt.value
                )
            else:
                # because long reads are autohandled, we must keep adding data until the operation completes.
                self._loop.call_soon_threadsafe(self._buffer_data.extend, evt.value)
        elif evt == "bt_evt_gatt_descriptor":
            uus = _bgapi_uuid_to_str(evt.uuid)
            # Unlike with services, we don't have enough information to directly create the BleakDescriptor here.
            self._loop.call_soon_threadsafe(
                self._buffer_descriptors.append,
                PartialDescriptor(uuid=uus, handle=evt.descriptor),
            )
        elif evt == "bt_evt_gatt_procedure_completed":
            self._loop.call_soon_threadsafe(self._ev_gatt_op.set)
        else:
            # Loudly show all the places we're not handling things yet!
            self.log.warning(f"unhandled bgapi evt! {evt}")

    @property
    def mtu_size(self) -> int:
        """Get ATT MTU size for active connection"""
        if self._mtu_size is None:
            # You normally get this event straight after connecting,
            warnings.warn(
                "bt_evt_gatt_mtu_exchanged not yet received! assuming default!"
            )
            return 23

        return self._mtu_size

    async def pair(self, *args, **kwargs) -> bool:
        raise NotImplementedError

    async def unpair(self) -> bool:
        raise NotImplementedError

    @property
    def is_connected(self) -> bool:
        # TODO - could also look at ev_disconnected.is_set()?
        return self._ch is not None

    async def get_services(self, **kwargs) -> BleakGATTServiceCollection:
        if self._services_resolved:
            return self.services

        self._ev_gatt_op.clear()
        self._bgh.lib.bt.gatt.discover_primary_services(self._ch)
        await self._ev_gatt_op.wait()

        for s in self.services:
            self._ev_gatt_op.clear()
            self._buffer_characteristics.clear()
            self._bgh.lib.bt.gatt.discover_characteristics(self._ch, s.handle)
            await self._ev_gatt_op.wait()

            # ok, we've now got a stack of partial characteristics
            for pc in self._buffer_characteristics:
                bc = BleakGATTCharacteristicBGAPI(
                    pc, s.uuid, s.handle, self.mtu_size - 3
                )
                self.services.add_characteristic(bc)  # Add to the root collection!

                # Now also get the descriptors
                self._ev_gatt_op.clear()
                self._buffer_descriptors.clear()
                self._bgh.lib.bt.gatt.discover_descriptors(self._ch, bc.handle)
                await self._ev_gatt_op.wait()
                for pd in self._buffer_descriptors:
                    bd = BleakGATTDescriptorBGAPI(pd, bc.uuid, bc.handle)
                    self.services.add_descriptor(bd)  # Add to the root collection!

        self._services_resolved = True
        return self.services

    async def read_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        **kwargs,
    ) -> bytearray:
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} was not found!".format(char_specifier))

        # this will automatically use long reads if needed, so need to make sure that we bunch up data
        self._ev_gatt_op.clear()
        self._buffer_data.clear()
        self._bgh.lib.bt.gatt.read_characteristic_value(self._ch, characteristic.handle)
        d, p = await asyncio.wait([asyncio.Task(self._ev_gatt_op.wait(), name="gattop"), asyncio.Task(self._ev_disconnected.wait(), name="disconn")],
                           return_when=asyncio.FIRST_COMPLETED)
        [t.cancel() for t in p]
        if self._ev_disconnected.is_set():
            pass  # nothing we can do differently here.
        return bytearray(self._buffer_data)

    async def read_gatt_descriptor(self, handle: int, **kwargs) -> bytearray:
        raise NotImplementedError

    async def write_gatt_char(
        self,
        char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID],
        data: Union[bytes, bytearray, memoryview],
        response: bool = False,
    ) -> None:
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} was not found!".format(char_specifier))

        if (
            GattCharacteristicsFlags.write.name not in characteristic.properties
            and GattCharacteristicsFlags.write_without_response.name
            not in characteristic.properties
        ):
            raise BleakError(
                f"Characteristic {characteristic} does not support write operations!"
            )
        if (
            not response
            and GattCharacteristicsFlags.write_without_response.name
            not in characteristic.properties
        ):
            # Warning seems harsh, this is just magically "fixing" things, but it's what the bluez backend does.
            self.log.warning(
                f"Characteristic {characteristic} does not support write without response, auto-trying as write"
            )
            response = True
        # bgapi needs "bytes" or a string that it will encode as latin1.
        # All of the bleak types can be cast to bytes, and that's easier than modifying pybgapi
        odata = bytes(data)
        if response:
            self._ev_gatt_op.clear()
            self._bgh.lib.bt.gatt.write_characteristic_value(
                self._ch, characteristic.handle, odata
            )
            d, p = await asyncio.wait([asyncio.Task(self._ev_gatt_op.wait(), name="gattop"), asyncio.Task(self._ev_disconnected.wait(), name="disconn")],
                               return_when=asyncio.FIRST_COMPLETED)
            [t.cancel() for t in p]
            if self._ev_disconnected.is_set():
                pass  # Nothing special we can do anyway.
        else:
            self._bgh.lib.bt.gatt.write_characteristic_value_without_response(
                self._ch, characteristic.handle, odata
            )

    async def write_gatt_descriptor(
        self, handle: int, data: Union[bytes, bytearray, memoryview]
    ) -> None:
        raise NotImplementedError

    async def start_notify(
        self,
        characteristic: BleakGATTCharacteristic,
        callback: NotifyCallback,
        **kwargs,
    ) -> None:
        self._cbs_notify[characteristic.handle] = callback
        enable = self._bgh.lib.bt.gatt.CLIENT_CONFIG_FLAG_NOTIFICATION
        force_indic = kwargs.get("force_indicate", False)
        if force_indic:
            enable = self._bgh.lib.bt.gatt.CLIENT_CONFIG_FLAG_INDICATION
        self._bgh.lib.bt.gatt.set_characteristic_notification(
            self._ch, characteristic.handle, enable
        )

    async def stop_notify(
        self, char_specifier: Union[BleakGATTCharacteristic, int, str, uuid.UUID]
    ) -> None:
        if not isinstance(char_specifier, BleakGATTCharacteristic):
            characteristic = self.services.get_characteristic(char_specifier)
        else:
            characteristic = char_specifier
        if not characteristic:
            raise BleakError("Characteristic {} was not found!".format(char_specifier))
        self._cbs_notify.pop(characteristic.handle, None)  # hard remove callback
        cancel = self._bgh.lib.bt.gatt.CLIENT_CONFIG_FLAG_DISABLE
        self._bgh.lib.bt.gatt.set_characteristic_notification(
            self._ch, characteristic.handle, cancel
        )
