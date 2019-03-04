#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `bleak` package."""

import os
import platform

import pytest

_IS_CI = os.environ.get("CI", "false").lower() == "true"
_IS_TRAVIS = os.environ.get("TRAVIS", "false").lower() == "true"
_IS_APPVEYOR = os.environ.get("APPVEYOR", "false").lower() == "true"
_IS_AZURE_PIPELINES = os.environ.get("AZURE_PIPELINES", "false").lower() == "true"


@pytest.mark.skipif(
    condition=_IS_CI and (_IS_TRAVIS or _IS_APPVEYOR or _IS_AZURE_PIPELINES),
    reason="Cannot run on CI systems with Ubuntu 16.04 installed.",
)
def test_import():
    """Test by importing the client and assert correct client by OS."""
    if platform.system() == "Linux":
        from bleak import BleakClient

        assert BleakClient.__name__ == "BleakClientBlueZDBus"
    elif platform.system() == "Windows":
        from bleak import BleakClient

        assert BleakClient.__name__ == "BleakClientDotNet"
    elif platform.system() == "Darwin":
        from bleak import BleakClient

        assert BleakClient.__name__ == "BleakClientCoreBluetooth"
