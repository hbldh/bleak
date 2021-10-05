#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `bleak` package."""

import os
import platform


_IS_CI = os.environ.get("CI", "false").lower() == "true"


def test_import():
    """Test by importing the client and assert correct client by OS."""
    if platform.system() == "Linux":
        from bleak import BleakClient

        assert BleakClient.__name__ == "BleakClientBlueZDBus"
    elif platform.system() == "Windows":
        from bleak import BleakClient

        assert BleakClient.__name__ == "BleakClientWinRT"
    elif platform.system() == "Darwin":
        from bleak import BleakClient

        assert BleakClient.__name__ == "BleakClientCoreBluetooth"
