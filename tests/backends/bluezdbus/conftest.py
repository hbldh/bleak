"""Shared fixtures and helpers for the BlueZ D-Bus backend tests.

The backend only imports on Linux, so it is imported lazily where needed.
"""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import contextlib
from collections.abc import AsyncIterator

import pytest

if TYPE_CHECKING:
    from bleak.backends.bluezdbus.manager import BlueZManager

ADAPTER_PATH = "/org/bluez/hci0"
DEVICE_ADDRESS = "AA:BB:CC:DD:EE:FF"
DEVICE_PATH = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"


def noop_characteristic_value_changed(char_path: str, value: bytes) -> None:
    pass


def get_watcher_task(manager: "BlueZManager") -> "asyncio.Task[None]":
    task = manager._bus_watcher_task  # pyright: ignore[reportPrivateUsage]
    assert task is not None
    return task


async def reap_watcher_task(manager: "BlueZManager") -> None:
    """Cancel and await the bus watcher task so it does not leak."""
    task = manager._bus_watcher_task  # pyright: ignore[reportPrivateUsage]
    if task is not None and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def release_manager(manager: "BlueZManager") -> None:
    """Reap the watcher task and disconnect the bus of a finished manager."""
    await reap_watcher_task(manager)
    bus = manager._bus  # pyright: ignore[reportPrivateUsage]
    if bus is not None:
        with contextlib.suppress(Exception):
            bus.disconnect()


def watch_connected(manager: "BlueZManager") -> list[bool]:
    """Records "Connected" changes reported for the test device."""
    changes: list[bool] = []
    manager.add_device_watcher(
        DEVICE_PATH, changes.append, noop_characteristic_value_changed
    )
    return changes


async def init_manager_on_closed_loop() -> (
    "tuple[BlueZManager, asyncio.AbstractEventLoop]"
):
    """Initializes a manager on its own loop and closes it with the watcher parked."""
    from bleak.backends.bluezdbus.manager import BlueZManager

    def init() -> tuple[BlueZManager, asyncio.AbstractEventLoop]:
        own_loop = asyncio.new_event_loop()
        manager = BlueZManager()
        own_loop.run_until_complete(manager.async_init())
        own_loop.run_until_complete(asyncio.sleep(0))  # park the watcher
        own_loop.close()
        return manager, own_loop

    return await asyncio.get_running_loop().run_in_executor(None, init)


@pytest.fixture
async def global_instances() -> (
    "AsyncIterator[dict[asyncio.AbstractEventLoop, BlueZManager]]"
):
    """The global manager registry, with this loop's entry reaped at teardown."""
    from bleak.backends.bluezdbus import manager as manager_module

    instances = manager_module._global_instances  # pyright: ignore[reportPrivateUsage]

    yield instances

    manager = instances.pop(asyncio.get_running_loop(), None)
    if manager is not None:
        await release_manager(manager)
