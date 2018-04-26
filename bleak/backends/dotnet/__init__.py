# -*- coding: utf-8 -*-
"""
__init__.py

Created on 2017-11-19 by hbldh <henrik.blidh@nedomkull.com>

"""
import sys
import pathlib
import logging

import clr

logger = logging.getLogger(__name__)
_here = pathlib.Path(__file__).parent

# BleakUWPBridge
sys.path.append(str(pathlib.Path(__file__).parent))
clr.AddReference("BleakUWPBridge")
