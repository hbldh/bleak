"""Regression test for <https://github.com/hbldh/bleak/issues/2021>."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import logging

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)

from bleak import BleakScanner
from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.manager import BlueZManager
from bleak.exc import BleakDBusError

from .conftest import ADAPTER_PATH
from .fake_bluez import StartDaemon

LOGGER = "bleak.backends.bluezdbus.manager"


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]


async def test_stop_recovers_from_one_in_progress(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    BlueZ answers StopDiscovery with InProgress when the kernel has already
    stopped scanning on its own. stop() must start and stop again to clear
    bluetoothd's stale discovery state, then return normally.
    """
    daemon = await start_daemon()
    daemon.adapter.errors["StopDiscovery"] = [defs.BLUEZ_ERROR_IN_PROGRESS]

    scanner = BleakScanner()
    await scanner.start()

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        await scanner.stop()

    assert daemon.adapter.calls == [
        "SetDiscoveryFilter",
        "StartDiscovery",
        "StopDiscovery",
        "StartDiscovery",
        "StopDiscovery",
        "SetDiscoveryFilter",
    ]
    assert not _warnings(caplog)


async def test_stop_raises_when_discovery_state_is_stuck(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    If the stop after the start is rejected too, bluetoothd's discovery state
    is stuck and no scan will work, so stop() must raise and log a warning
    that says what to do.
    """
    daemon = await start_daemon()
    daemon.adapter.errors["StopDiscovery"] = [
        defs.BLUEZ_ERROR_IN_PROGRESS,
        defs.BLUEZ_ERROR_IN_PROGRESS,
    ]

    scanner = BleakScanner()
    await scanner.start()

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        with pytest.raises(BleakDBusError) as info:
            await scanner.stop()

    assert info.value.dbus_error == defs.BLUEZ_ERROR_IN_PROGRESS
    assert daemon.adapter.calls == [
        "SetDiscoveryFilter",
        "StartDiscovery",
        "StopDiscovery",
        "StartDiscovery",
        "StopDiscovery",
    ]
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "stuck" in warnings[0] and ADAPTER_PATH in warnings[0]


async def test_stop_returns_when_retry_start_fails(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    If the StartDiscovery used to recover from InProgress fails, scanning is
    still stopped, so stop() must not raise an error from a call the user
    did not make, but it must warn since the next scan may not work.
    """
    daemon = await start_daemon()
    daemon.adapter.errors["StopDiscovery"] = [defs.BLUEZ_ERROR_IN_PROGRESS]
    daemon.adapter.errors["StartDiscovery"] = [None, defs.BLUEZ_ERROR_IN_PROGRESS]

    scanner = BleakScanner()
    await scanner.start()

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        await scanner.stop()

    assert daemon.adapter.calls == [
        "SetDiscoveryFilter",
        "StartDiscovery",
        "StopDiscovery",
        "StartDiscovery",
    ]
    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert "StartDiscovery" in warnings[0] and ADAPTER_PATH in warnings[0]
    assert "[org.bluez.Error.InProgress] fake StartDiscovery error" in warnings[0]


async def test_stop_still_raises_other_errors(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
) -> None:
    daemon = await start_daemon()
    daemon.adapter.errors["StopDiscovery"] = [defs.BLUEZ_ERROR_FAILED]

    scanner = BleakScanner()
    await scanner.start()

    with pytest.raises(BleakDBusError) as info:
        await scanner.stop()

    assert info.value.dbus_error == defs.BLUEZ_ERROR_FAILED
    assert daemon.adapter.calls == [
        "SetDiscoveryFilter",
        "StartDiscovery",
        "StopDiscovery",
    ]
