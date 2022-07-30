#!/usr/bin/env python

"""Tests for `bleak.backends.bluezdbus.version` package."""

import sys
from unittest.mock import Mock, patch

import pytest

if sys.version_info[:2] < (3, 8):
    from asynctest.mock import CoroutineMock as AsyncMock
else:
    from unittest.mock import AsyncMock

from bleak.backends.bluezdbus.version import BlueZFeatures


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "version,can_write_without_response,write_without_response_workaround_needed,hides_battery_characteristic,hides_device_name_characteristic",
    [
        (b"bluetoothctl: 5.34", False, False, False, False),
        (b"bluetoothctl: 5.46", True, False, False, False),
        (b"bluetoothctl: 5.48", True, False, True, True),
        (b"bluetoothctl: 5.51", True, True, True, True),
        (b"bluetoothctl: 5.63", True, True, True, True),
        (b"", True, True, True, True),
    ],
)
async def test_bluez_version(
    version,
    can_write_without_response,
    write_without_response_workaround_needed,
    hides_battery_characteristic,
    hides_device_name_characteristic,
):
    """Test we can determine supported feature from bluetoothctl."""
    mock_proc = Mock(
        wait=AsyncMock(), stdout=Mock(read=AsyncMock(return_value=version))
    )
    with patch(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_proc),
    ):
        BlueZFeatures._check_bluez_event = None
        await BlueZFeatures.check_bluez_version()
    assert BlueZFeatures.checked_bluez_version is True
    assert BlueZFeatures.can_write_without_response == can_write_without_response
    assert (
        not BlueZFeatures.write_without_response_workaround_needed
        == write_without_response_workaround_needed
    )
    assert BlueZFeatures.hides_battery_characteristic == hides_battery_characteristic
    assert (
        BlueZFeatures.hides_device_name_characteristic
        == hides_device_name_characteristic
    )


@pytest.mark.asyncio
async def test_bluez_version_only_happens_once():
    """Test we can determine supported feature from bluetoothctl."""
    BlueZFeatures.checked_bluez_version = False
    BlueZFeatures._check_bluez_event = None
    mock_proc = Mock(
        wait=AsyncMock(),
        stdout=Mock(read=AsyncMock(return_value=b"bluetoothctl: 5.46")),
    )
    with patch(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_proc),
    ):
        await BlueZFeatures.check_bluez_version()

    assert BlueZFeatures.checked_bluez_version is True

    with patch(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        side_effect=Exception,
    ):
        await BlueZFeatures.check_bluez_version()

    assert BlueZFeatures.checked_bluez_version is True


@pytest.mark.asyncio
async def test_exception_checking_bluez_features_does_not_block_forever():
    """Test an exception while checking BlueZ features does not stall a second check."""
    BlueZFeatures.checked_bluez_version = False
    BlueZFeatures._check_bluez_event = None
    with patch(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        side_effect=OSError,
    ):
        await BlueZFeatures.check_bluez_version()

    assert BlueZFeatures.checked_bluez_version is True

    with patch(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        side_effect=OSError,
    ):
        await BlueZFeatures.check_bluez_version()

    assert BlueZFeatures.checked_bluez_version is True
