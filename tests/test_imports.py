#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `bleak` package."""

import os
import platform

import pytest


@pytest.mark.skipif(
    condition=bool(os.environ.get('CI', "false").lower() == "true") and (
        bool(os.environ.get('TRAVIS', "false").lower() == "true")
        or bool(os.environ.get('APPVEYOR', "false").lower() == "true")
    ),
    reason="Cannot run on Travis CI (has BlueZ 4.101 <= 5.43) or on Appveyor (runs Windows < 10)."
)
def test_import():
    """Test by importing the client and assert correct client by OS."""
    if platform.system() == 'Linux':
        from bleak import BleakClient
        assert BleakClient.__name__ == 'BleakClientBlueZDBus'
    elif platform.system() == 'Windows':
        from bleak import BleakClient
        assert BleakClient.__name__ == 'BleakClientDotNet'
    elif platform.system() == 'Darwin':
        from bleak import BleakClient
        assert BleakClient.__name__ == 'BleakClientCoreBluetooth'
