#!/usr/bin/env python

"""Tests for `bleak.backends.bluezdbus.version` package."""

import sys

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)
    assert False  # HACK: work around pyright bug

from unittest.mock import AsyncMock, Mock

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
    monkeypatch: pytest.MonkeyPatch,
):
    """Test we can determine supported feature from bluetoothctl."""
    mock_proc = Mock(
        wait=AsyncMock(), stdout=Mock(read=AsyncMock(return_value=version))
    )
    monkeypatch.setattr(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_proc),
    )
    await BlueZFeatures.check_bluez_version()
    assert BlueZFeatures.checked_bluez_version is True


@pytest.mark.asyncio
async def test_bluez_version_only_happens_once(monkeypatch: pytest.MonkeyPatch):
    """Test we can determine supported feature from bluetoothctl."""
    mock_proc = Mock(
        wait=AsyncMock(),
        stdout=Mock(read=AsyncMock(return_value=b"bluetoothctl: 5.46")),
    )
    monkeypatch.setattr(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_proc),
    )
    await BlueZFeatures.check_bluez_version()

    assert BlueZFeatures.checked_bluez_version is True

    monkeypatch.setattr(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        AsyncMock(side_effect=Exception),
    )
    await BlueZFeatures.check_bluez_version()

    assert BlueZFeatures.checked_bluez_version is True


@pytest.mark.asyncio
async def test_exception_checking_bluez_features_does_not_block_forever(
    monkeypatch: pytest.MonkeyPatch,
):
    """Test an exception while checking BlueZ features does not stall a second check."""
    monkeypatch.setattr(
        "bleak.backends.bluezdbus.version.asyncio.create_subprocess_exec",
        AsyncMock(side_effect=OSError),
    )
    await BlueZFeatures.check_bluez_version()

    assert BlueZFeatures.checked_bluez_version is True

    await BlueZFeatures.check_bluez_version()

    assert BlueZFeatures.checked_bluez_version is True
