#!/usr/bin/env python

"""Tests for `bleak.backends.bluezdbus.version` package."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from bleak.backends.bluezdbus.version import BlueZFeatures


@pytest.fixture(autouse=True)
def reset_bluez_features(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset BlueZFeatures class variables to avoid side effects between tests."""
    monkeypatch.setattr(BlueZFeatures, "checked_bluez_version", False)
    monkeypatch.setattr(BlueZFeatures, "_check_bluez_event", None)
    monkeypatch.setattr(BlueZFeatures, "supported_version", True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "version",
    [
        (b"bluetoothctl: 5.51"),
        (b"bluetoothctl: 5.63"),
        (b""),
    ],
)
async def test_bluez_version(
    version: bytes,
):
    """Test we can determine supported feature from bluetoothctl."""
    mock_proc = Mock(
        wait=AsyncMock(), stdout=Mock(read=AsyncMock(return_value=version))
    )
    with patch(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_proc),
    ):
        await BlueZFeatures.check_bluez_version()
    assert BlueZFeatures.checked_bluez_version is True


@pytest.mark.asyncio
async def test_bluez_version_only_happens_once():
    """Test we can determine supported feature from bluetoothctl."""
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
