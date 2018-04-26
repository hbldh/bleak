#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `bleak` package."""

import platform

from bleak import BleakClient


def test_import():
    """Test by importing the client and assert correct client by OS."""
    if platform.system() == 'Linux':
        assert BleakClient.__name__ == 'BleakClientBlueZDBus'
    elif platform.system() == 'Windows':
        assert BleakClient.__name__ == 'BleakClientDotNet'
    elif platform.system() == 'Darwin':
        assert BleakClient.__name__ == 'BleakClientCoreBluetooth'
