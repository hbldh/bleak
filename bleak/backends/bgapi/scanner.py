import asyncio
import logging
import os
import struct
import sys
from typing import List, Optional
import uuid

import bgapi

if sys.version_info[:2] < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal

from ...exc import BleakError
from ..scanner import AdvertisementData, AdvertisementDataCallback, BaseBleakScanner
from . import BgapiRegistry


class BleakScannerBGAPI(BaseBleakScanner):
    """
    A scanner built to talk to a Silabs "BGAPI" NCP device.
    """

    def __init__(
        self,
        detection_callback: Optional[AdvertisementDataCallback],
        service_uuids: Optional[List[str]],
        scanning_mode: Literal["active", "passive"],
        **kwargs,
    ):

        super(BleakScannerBGAPI, self).__init__(detection_callback, service_uuids)
        self._adapter: Optional[str] = kwargs.get("adapter", kwargs.get("ncp"))
        tag = kwargs.get("logtag", hex(id(self)))
        self.log = logging.getLogger(f"bleak.backends.bgapi.scanner.{tag}")

        # Env vars have priority
        self._bgapi = os.environ.get("BLEAK_BGAPI_XAPI", kwargs.get("bgapi", None))
        if not self._bgapi:
            raise BleakError(
                "BGAPI file for your target (sl_bt.xapi) is required, normally this is in your SDK tree"
            )
        self._adapter = os.environ.get(
            "BLEAK_BGAPI_ADAPTER", kwargs.get("adapter", "/dev/ttyACM0")
        )

        self._loop = asyncio.get_running_loop()
        self._bgh = BgapiRegistry.get(self._adapter, self._bgapi)

        scan_modes = {
            "passive": self._bgh.lib.bt.scanner.SCAN_MODE_SCAN_MODE_PASSIVE,
            "active": self._bgh.lib.bt.scanner.SCAN_MODE_SCAN_MODE_ACTIVE,
        }
        # TODO - might make this a "backend option"?
        # self._phy = self._lib.bt.scanner.SCAN_PHY_SCAN_PHY_1M_AND_CODED
        self._phy = self._bgh.lib.bt.scanner.SCAN_PHY_SCAN_PHY_1M
        # TODO - might make this a "backend option"?
        # Discover mode seems to be an internal filter on what it sees?
        # maybe use the "filters" blob for this?
        # I definitely need OBSERVATION for my own stuff at least.
        # self._discover_mode = self._lib.bt.scanner.DISCOVER_MODE_DISCOVER_GENERIC
        self._discover_mode = self._bgh.lib.bt.scanner.DISCOVER_MODE_DISCOVER_OBSERVATION
        self._scanning_mode = scan_modes.get(scanning_mode, scan_modes["passive"])
        if scanning_mode == "passive" and service_uuids:
            self.log.warning(
                "service uuid filtering with passive scanning is super unreliable..."
            )

        # Don't bother supporting the deprecated set_scanning_filter in new work.
        self._scanning_filters = {}
        filters = kwargs.get("filters")
        if filters:
            self._scanning_filters = filters

    def _bgapi_evt_handler(self, evt):
        """
        THIS RUNS IN THE BGLIB THREAD!
        and because of this, we can't call commands from here ourself, we'd have to
        recall them back onto the other thread?
        """
        if evt == "bt_evt_system_boot":
            # This handles starting scanning if we were reset...
            self.log.debug(
                "NCP booted: %d.%d.%db%d hw:%d hash: %x",
                evt.major,
                evt.minor,
                evt.patch,
                evt.build,
                evt.hw,
                evt.hash,
            )
        elif (
            evt == "bt_evt_scanner_legacy_advertisement_report"
            or evt == "bt_evt_scanner_extended_advertisement_report"
        ):
            rssif = self._scanning_filters.get("rssi", -255)
            addr_match = self._scanning_filters.get("address", False)
            addr_matches = True
            if addr_match and addr_match != evt.address:
                addr_matches = False
            if evt.rssi > rssif and addr_matches:
                self._loop.call_soon_threadsafe(
                    self._handle_advertising_data, evt, evt.data
                )
        else:
            self.log.warning(f"unhandled bgapi evt! {evt}")

    async def start(self):
        await self._bgh.start_scan(self._phy, self._scanning_mode, self._discover_mode, self._bgapi_evt_handler)

    async def stop(self):
        await self._bgh.stop_scan(self._bgapi_evt_handler)

    def set_scanning_filter(self, **kwargs):
        # BGAPI doesn't do any itself, but doing it bleak can still be very userfriendly.
        self._scanning_filters = kwargs
        # raise NotImplementedError("BGAPI doesn't provide NCP level filters")

    def _handle_advertising_data(self, evt, raw):
        """
        Make a bleak AdvertisementData() from our raw data, we'll fill in what we can.
        :param data:
        :return:
        """

        items = {}
        index = 0
        # TODO make this smarter/faster/simpler
        while index < len(raw):
            remaining = raw[index:]
            flen = remaining[0]
            index = index + flen + 1  # account for length byte too!
            if flen == 0:
                continue
            chunk = remaining[1 : 1 + flen]
            type = chunk[0]
            dat = chunk[1:]
            items[type] = (type, dat)

        flags = None
        local_name = None
        service_uuids = []
        manufacturer_data = {}
        tx_power = None
        service_data = {}

        for type, dat in items.values():
            # Ok, do a little extra magic?
            # Assigned numbers sec 2.3
            if type == 1:
                assert len(dat) == 1
                flags = dat[0]
            elif type in [0x2, 0x3]:
                num = len(dat) // 2
                uuids16 = [struct.unpack_from("<H", dat, a * 2)[0] for a in range(num)]
                service_uuids.extend(
                    [f"0000{a:04x}-0000-1000-8000-00805f9b34fb" for a in uuids16]
                )
            elif type in [4, 5]:
                num = len(dat) // 4
                uuids32 = [struct.unpack_from("<L", dat, a * 2)[0] for a in range(num)]
                service_uuids.extend(
                    [f"{a:08x}-0000-1000-8000-00805f9b34fb" for a in uuids32]
                )
            elif type in [6, 7]:
                # FIXME - can we have multiple 128bits in the advertisement?
                assert len(dat) == 16
                # Thanks for the reversal silabs.
                service_uuids.extend([f"{uuid.UUID(bytes=bytes(reversed(dat)))}"])
            elif type in [0x08, 0x09]:
                # FIXME - um, shortened name? do we just call that local name?
                # XXX - sometimes we get trailing zero bytes here? just remove them.
                local_name = dat.decode("utf8").rstrip("\0")
            elif type == 0x0A:
                (tx_power,) = struct.unpack_from("<b", dat, 0)
            elif type == 0x16:
                (uuid16,) = struct.unpack("<H", dat[:2])
                service_data[f"0000{uuid16:04x}-0000-1000-8000-00805f9b34fb"] = dat[2:]
            elif type == 0x1b:
                # LE device address is used by SiLabs Apploader at least.
                bdaddr_flags = dat[0]
                bdaddr_le = struct.unpack("<6B", dat[1:])  ## reversed order?
                #logging.debug("ignoring LE device address as uninteresting: flags: %x, addr: %s", bdaddr_flags, bdaddr_le)
            elif type == 0x20:
                (uuid32,) = struct.unpack("<H", dat[:4])
                service_data[f"{uuid32:084x}-0000-1000-8000-00805f9b34fb"] = dat[4:]
            elif type == 0x21:
                # FIXME untested
                uuid128 = f"{uuid.UUID(bytes=bytes(reversed(dat[0:16])))}"
                service_data[uuid128] = dat[16:]
                self.log.warning("Untested 128bit service data! %s", service_data)
            elif type == 0xFF:
                (vendor,) = struct.unpack("<H", dat[0:2])
                manufacturer_data[vendor] = dat[2:]
            else:
                self.log.debug(
                    "Unhandled advertising type: %d(%#x) of len %d",
                    type,
                    type,
                    len(dat),
                )

        advertisement_data = AdvertisementData(
            local_name=local_name,
            manufacturer_data=manufacturer_data,
            service_data=service_data,
            service_uuids=service_uuids,
            tx_power=tx_power,
            rssi=evt.rssi,
            platform_data=(dict(flags=flags),),  # do we need/want more?
        )
        ea = evt.address.upper()
        devname = local_name if local_name else ea.replace(":", "-").upper()
        device = self.create_or_update_device(
            ea, devname, ea, advertisement_data
        )
        if self._callback is None:
            return

        self._callback(device, advertisement_data)
