"""Tests for BlueZManager bus loss handling against a real dbus-daemon."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
from collections.abc import AsyncIterator

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)

from bleak._compat import timeout as async_timeout
from bleak.backends.bluezdbus import manager as manager_module
from bleak.backends.bluezdbus.manager import BlueZManager

from .conftest import (
    DEVICE_PATH,
    get_watcher_task,
    init_manager_on_closed_loop,
    release_manager,
    watch_connected,
)
from .fake_bluez import StartDaemon


@pytest.fixture
async def manager() -> AsyncIterator[BlueZManager]:
    manager = BlueZManager()

    yield manager

    await release_manager(manager)


async def test_manager_recovers_from_real_dbus_daemon_death(
    start_daemon: StartDaemon, manager: BlueZManager
) -> None:
    daemon = await start_daemon()
    await manager.async_init()
    assert manager.is_connected(DEVICE_PATH) is True

    connected_changes = watch_connected(manager)
    watcher_task = get_watcher_task(manager)

    # A real socket death, through the real dbus_fast reader
    daemon.kill()
    async with async_timeout(10):
        await watcher_task

    assert connected_changes == [False]
    assert manager.is_connected(DEVICE_PATH) is False
    assert manager._properties == {}  # pyright: ignore[reportPrivateUsage]

    # A new daemon comes up at a new address; async_init recovers
    daemon = await start_daemon()
    async with async_timeout(10):
        await manager.async_init()

    assert manager.is_connected(DEVICE_PATH) is True

    # the watcher registered before the loss still gets real signals on
    # the new bus, exercising the match rules added by async_init
    daemon.device.disconnect()
    async with async_timeout(10):
        while len(connected_changes) < 2:
            await asyncio.sleep(0.01)

    assert connected_changes == [False, False]
    assert manager.is_connected(DEVICE_PATH) is False


async def test_async_init_notifies_watchers_when_it_sees_daemon_death_first(
    start_daemon: StartDaemon, manager: BlueZManager
) -> None:
    daemon = await start_daemon()
    await manager.async_init()
    bus = manager._bus  # pyright: ignore[reportPrivateUsage]
    assert bus is not None

    connected_changes = watch_connected(manager)
    watcher_task = get_watcher_task(manager)

    # The replacement is already up when the first daemon dies
    await start_daemon()
    daemon.kill()

    # Wait for the reader to see the EOF, but not for the watcher task.
    # The reader resolves the disconnect future in its callback, which queues
    # the watcher wakeup behind this task's sleep(0) wakeup since the ready
    # queue is FIFO. A non-zero sleep would let the watcher run first.
    async with async_timeout(10):
        while bus.connected:
            await asyncio.sleep(0)
    if watcher_task.done():
        pytest.fail("the watcher task ran before async_init could see the dead bus")

    async with async_timeout(10):
        await manager.async_init()

    assert watcher_task.done()
    assert connected_changes == [False]
    assert manager.is_connected(DEVICE_PATH) is True


async def test_global_manager_cleans_up_closed_loop_with_real_bus(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
) -> None:
    """Finalizing the stale bus wakes its watcher task on the closed loop."""
    await start_daemon()
    stale_manager, closed_loop = await init_manager_on_closed_loop()
    assert not get_watcher_task(stale_manager).done()
    global_instances[closed_loop] = stale_manager

    manager = await manager_module.get_global_bluez_manager()

    assert closed_loop not in global_instances
    # the stale bus was released before the wakeup failed
    stale_bus = stale_manager._bus  # pyright: ignore[reportPrivateUsage]
    assert stale_bus is not None and stale_bus.connected is False
    assert manager.is_connected(DEVICE_PATH) is True
