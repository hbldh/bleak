# -*- coding: utf-8 -*-
"""
__init__.py

Created on 2017-11-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "darwin":
        assert False, "This backend is only available on macOS"

import objc

objc.options.verbose = True
