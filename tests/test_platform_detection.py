#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `bleak` package."""

import platform

from bleak.backends import get_backend


def test_platform_detection():
    """Test by importing the client and assert correct client by OS."""

    client_backend_type = get_backend().client_type
    scanner_backend_type = get_backend().scanner_type

    if platform.system() == "Linux":
        assert client_backend_type.__name__ == "BleakClientBlueZDBus"
        assert scanner_backend_type.__name__ == "BleakScannerBlueZDBus"
    elif platform.system() == "Windows":
        assert client_backend_type.__name__ == "BleakClientWinRT"
        assert scanner_backend_type.__name__ == "BleakScannerWinRT"
    elif platform.system() == "Darwin":
        assert client_backend_type.__name__ == "BleakClientCoreBluetooth"
        assert scanner_backend_type.__name__ == "BleakScannerCoreBluetooth"
