#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `bleak` package."""

import os
import platform

import pytest

_IS_CI = os.environ.get('CI', "false").lower() == "true"
_IS_TRAVIS =os.environ.get('TRAVIS', "false").lower() == "true"
_IS_APPVEYOR = os.environ.get('APPVEYOR', "false").lower() == "true"


@pytest.mark.skipif(
    condition=_IS_CI and (_IS_TRAVIS or _IS_APPVEYOR),
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
