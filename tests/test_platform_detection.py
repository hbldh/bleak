#!/usr/bin/env python

"""Tests for `bleak` package."""

import platform

import pytest

from bleak import BleakClient, BleakScanner
from bleak.backends import BleakBackend
from bleak.backends.adapter import get_platform_adapter_backend_type
from bleak.backends.client import get_platform_client_backend_type
from bleak.backends.scanner import get_platform_scanner_backend_type


def test_platform_detection():
    """Test by importing the client and assert correct client by OS."""

    client_backend_type, client_backend_id = get_platform_client_backend_type()
    scanner_backend_type, scanner_backend_id = get_platform_scanner_backend_type()
    adapter_backend_type, adapter_backend_id = get_platform_adapter_backend_type()

    if platform.system() == "Linux":
        assert client_backend_type.__name__ == "BleakClientBlueZDBus"
        assert scanner_backend_type.__name__ == "BleakScannerBlueZDBus"
        assert adapter_backend_type.__name__ == "BleakAdapterBlueZDBus"
        assert client_backend_id == BleakBackend.BLUEZ_DBUS
        assert scanner_backend_id == BleakBackend.BLUEZ_DBUS
        assert adapter_backend_id == BleakBackend.BLUEZ_DBUS
    elif platform.system() == "Windows":
        assert client_backend_type.__name__ == "BleakClientWinRT"
        assert scanner_backend_type.__name__ == "BleakScannerWinRT"
        assert adapter_backend_type.__name__ == "BleakAdapterWinRT"
        assert client_backend_id == BleakBackend.WIN_RT
        assert scanner_backend_id == BleakBackend.WIN_RT
        assert adapter_backend_id == BleakBackend.WIN_RT
    elif platform.system() == "Darwin":
        assert client_backend_type.__name__ == "BleakClientCoreBluetooth"
        assert scanner_backend_type.__name__ == "BleakScannerCoreBluetooth"
        assert adapter_backend_type.__name__ == "BleakAdapterCoreBluetooth"
        assert client_backend_id == BleakBackend.CORE_BLUETOOTH
        assert scanner_backend_id == BleakBackend.CORE_BLUETOOTH
        assert adapter_backend_id == BleakBackend.CORE_BLUETOOTH


@pytest.mark.asyncio
async def test_backend_id():
    """Test that backend IDs are correct."""
    client = BleakClient("")
    scanner = BleakScanner()

    assert client.backend_id == scanner.backend_id

    if platform.system() == "Linux":
        assert client.backend_id == BleakBackend.BLUEZ_DBUS
        assert scanner.backend_id == BleakBackend.BLUEZ_DBUS
    elif platform.system() == "Windows":
        assert client.backend_id == BleakBackend.WIN_RT
        assert scanner.backend_id == BleakBackend.WIN_RT
    elif platform.system() == "Darwin":
        assert client.backend_id == BleakBackend.CORE_BLUETOOTH
        assert scanner.backend_id == BleakBackend.CORE_BLUETOOTH
