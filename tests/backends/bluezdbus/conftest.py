"""Shared helpers for the BlueZ D-Bus backend tests."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import contextlib

if TYPE_CHECKING:
    from bleak.backends.bluezdbus.manager import BlueZManager

ADAPTER_PATH = "/org/bluez/hci0"
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
