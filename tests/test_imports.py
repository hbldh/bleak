#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `bleak` package."""

import os
import platform

import pytest

_IS_CI = os.environ.get("CI", "false").lower() == "true"
_OS = os.environ.get("AGENT_OS").lower()

@pytest.mark.skipif(
    condition=_IS_CI and _OS == 'linux',
    reason="Cannot run on Azure Pipelines with Ubuntu 16.04 installed."
)
@pytest.mark.skipif(
    condition=_IS_CI and _OS == 'darwin',
    reason="Cannot run on Azure Pipelines with Mac OS."
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
