#!/usr/bin/env python

"""Tests for `bleak.backends.winrt.util` package."""

import sys

import pytest

if not sys.platform.startswith("win"):
    pytest.skip("skipping windows-only tests", allow_module_level=True)

from ctypes import windll, wintypes

from bleak.backends.winrt.util import _check_hresult, assert_mta, uninitialize_sta
from bleak.exc import BleakError

# https://learn.microsoft.com/en-us/windows/win32/api/objbase/ne-objbase-coinit
COINIT_MULTITHREADED = 0x0
COINIT_APARTMENTTHREADED = 0x2

# https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-coinitializeex
_CoInitializeEx = windll.ole32.CoInitializeEx
_CoInitializeEx.restype = wintypes.LONG
_CoInitializeEx.argtypes = [wintypes.LPVOID, wintypes.DWORD]
_CoInitializeEx.errcheck = _check_hresult

# https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-couninitialize
_CoUninitialize = windll.ole32.CoUninitialize
_CoUninitialize.restype = None
_CoUninitialize.argtypes = []


@pytest.mark.asyncio
async def test_assert_mta_no_init():
    """Test device_path_from_characteristic_path."""

    await assert_mta()


@pytest.mark.asyncio
async def test_assert_mta_init_mta():
    """Test device_path_from_characteristic_path."""

    _CoInitializeEx(None, COINIT_MULTITHREADED)

    try:
        await assert_mta()
        assert hasattr(assert_mta, "_allowed")
    finally:
        _CoUninitialize()


@pytest.mark.asyncio
async def test_assert_mta_init_sta():
    """Test device_path_from_characteristic_path."""

    _CoInitializeEx(None, COINIT_APARTMENTTHREADED)

    try:
        with pytest.raises(
            BleakError,
            match="Thread is configured for Windows GUI but callbacks are not working.",
        ):
            await assert_mta()
    finally:
        _CoUninitialize()


@pytest.mark.asyncio
async def test_uninitialize_sta():
    """Test device_path_from_characteristic_path."""

    _CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    uninitialize_sta()

    await assert_mta()
