
"""
Perform Bluetooth LE Scan.

macOS

Created on 2019-06-24 by kevincar <kevincarrolldavis@gmail.com>

"""

import asyncio

from typing import List
from asyncio.events import AbstractEventLoop
from bleak.backends.device import BLEDevice

def discover(
        timeout: float = 5.0,
        loop: AbstractEventLoop = None,
        **kwargs) -> List[BLEDevice]:
    """Perform a Bluetooth LE Scan.

    Args:
        timeout (float): duration of scaning period
        loop (Event Loop): Event Loop to use

    """
    loop = loop if loop else asyncio.get_event_loop()

    print("Hi Mom")
    return
