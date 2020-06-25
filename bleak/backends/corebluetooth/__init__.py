# -*- coding: utf-8 -*-
"""
__init__.py

Created on 2017-11-19 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
from .CentralManagerDelegate import CentralManagerDelegate
import objc

objc.options.verbose = True


class Application:
    """
    This is a temporary application class responsible for running the NSRunLoop
    so that events within CoreBluetooth are appropriately handled
    """
    def __init__(self):
        self.central_manager_delegate = CentralManagerDelegate.alloc().init()


# Restructure this later: Global isn't the prettiest way of doing this...
global CBAPP
CBAPP = Application()
