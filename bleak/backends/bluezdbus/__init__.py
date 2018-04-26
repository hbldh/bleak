# -*- coding: utf-8 -*-
"""
__init__.py

Created on 2017-11-19 by hbldh <henrik.blidh@nedomkull.com>

"""

import asyncio
from twisted.internet import asyncioreactor as _asyncioreactor

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
_asyncioreactor.install(eventloop=loop)
from twisted.internet import reactor  # noqa
