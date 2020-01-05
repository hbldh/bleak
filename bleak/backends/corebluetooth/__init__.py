# -*- coding: utf-8 -*-
"""
__init__.py

Created on 2017-11-19 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
from Foundation import NSDate, NSDefaultRunLoopMode, NSRunLoop
from .CentralManagerDelegate import CentralManagerDelegate
import objc

objc.options.verbose = True


class Application:
    """
    This is a temporary application class responsible for running the NSRunLoop
    so that events within CoreBluetooth are appropriately handled
    """

    ns_run_loop_done = False
    ns_run_loop_interval = 0.001

    def __init__(self):
        self.main_loop = asyncio.get_event_loop()
        self.main_loop.create_task(self._handle_nsrunloop())
        self.main_loop.create_task(self._central_manager_delegate_ready())

        self.nsrunloop = NSRunLoop.currentRunLoop()

        self.central_manager_delegate = CentralManagerDelegate.alloc().init()

    def __del__(self):
        self.ns_run_loop_done = True

    async def _handle_nsrunloop(self):
        while not self.ns_run_loop_done:
            time_interval = NSDate.alloc().initWithTimeIntervalSinceNow_(
                self.ns_run_loop_interval
            )
            self.nsrunloop.runMode_beforeDate_(NSDefaultRunLoopMode, time_interval)
            await asyncio.sleep(0)

    async def _central_manager_delegate_ready(self):
        await self.central_manager_delegate.is_ready()


# Restructure this later: Global isn't the prettiest way of doing this...
global CBAPP
CBAPP = Application()
