"""
Backend targetting Silicon Labs devices running "NCP" firmware, using the BGAPI via pyBGAPI
See: https://pypi.org/project/pybgapi/
"""
import asyncio
import logging
import typing

import bgapi

class BgapiHandler():
    def __init__(self, adapter, xapi):
        self.log = logging.getLogger(f"BgapiHandler-{adapter}")
        self.log.info("creating an explicit handler")
        self._loop = asyncio.get_running_loop()

        self.lib = bgapi.BGLib(
            bgapi.SerialConnector(adapter, baudrate=115200),
            xapi,
            self.bgapi_evt_handler,
        )
        self._scan_handlers = list()
        self._is_scanning = False
        self.scan_phy = None
        self.scan_parameters = None
        self.scan_discover_mode = None
        # We should make _this_ layer do a .lib.open() straight away, so it can call reset...?
        # then it can manage start_scan
        self.lib.open()
        self.log.info("Opened.")
        self.is_booted = asyncio.Event()
        self.lib.bt.system.reset(0)
        # block other actions here til we get the booted message?
        self.log.info("Requested a reset to synchronize")

    def bgapi_evt_handler(self, evt):
        """
        THIS RUNS IN THE BGLIB THREAD!
        and because of this, we can't call commands from here ourself, we'd have to
        recall them back onto the other thread?
        """
        if evt == "bt_evt_system_boot":
            self.log.debug("booted, marking available")
            self._loop.call_soon_threadsafe(self.is_booted.set)

        #self.log.debug("Internal event received, sending to %d subs: %s", len(self._scan_handlers), evt)
        for x in self._scan_handlers:
            x(evt)
        #self.log.debug("int event finished")

    async def start_scan(self, phy, scanning_mode, discover_mode, handler: typing.Callable):
        """
        :return:
        """
        await self.is_booted.wait()
        self._scan_handlers.append(handler)
        if self._is_scanning:
            # TODO - If params are the same, return, if params are different....
            # reinitialize with new ones?  we're still by definition one app,
            # we must assume cooperative.
            self.log.debug("scanning already in process, skipping")
            return
        self._is_scanning = True
        self.log.debug("requesting bgapi to start scanning")
        self.scan_phy = phy
        self.scan_parameters = scanning_mode
        self.scan_discover_mode = discover_mode
        self.lib.bt.scanner.set_parameters(self.scan_parameters, 0x10, 0x10)
        self.lib.bt.scanner.start(self.scan_phy, self.scan_discover_mode)

    async def stop_scan(self, handler: typing.Callable):
        self._scan_handlers.remove(handler)
        if len(self._scan_handlers) == 0:
            self.log.info("Stopping scanners, all listeners have exited")
            self.lib.bt.scanner.stop()
            self._is_scanning = False



class BgapiRegistry:
    """
    Holds lib/connector instances based on the adapter address.
    Only allows one, so you can have multiple higher level objects...
    """
    registry = {}


    @classmethod
    def get(cls, adapter, xapi):
        x = cls.registry.get(adapter)
        if x:
            print("Returning existing instance: ", x)
            return x
        print("Creating a new bgapi chunk!")
        x = BgapiHandler(adapter, xapi)
        cls.registry[adapter] = x
        return x
