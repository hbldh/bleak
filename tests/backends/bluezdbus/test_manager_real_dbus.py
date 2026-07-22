"""Tests for BlueZManager bus loss handling against a real dbus-daemon."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import contextlib
import shutil
import subprocess

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)

if shutil.which("dbus-daemon") is None:
    pytest.skip("dbus-daemon is not available", allow_module_level=True)

from dbus_fast.aio.message_bus import MessageBus
from dbus_fast.annotations import DBusBool, DBusObjectPath, DBusStr
from dbus_fast.constants import BusType, PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property

from bleak._compat import timeout as async_timeout
from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.manager import BlueZManager

from .conftest import (
    ADAPTER_PATH,
    DEVICE_PATH,
    get_watcher_task,
    noop_characteristic_value_changed,
    reap_watcher_task,
)


class FakeAdapter1(ServiceInterface):
    """A stand-in for the BlueZ org.bluez.Adapter1 interface."""

    def __init__(self) -> None:
        super().__init__(defs.ADAPTER_INTERFACE)

    @dbus_property(access=PropertyAccess.READ)
    def Powered(self) -> DBusBool:
        return True


class FakeDevice1(ServiceInterface):
    """A stand-in for the BlueZ org.bluez.Device1 interface."""

    def __init__(self) -> None:
        super().__init__(defs.DEVICE_INTERFACE)

    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> DBusBool:
        return True

    @dbus_property(access=PropertyAccess.READ)
    def ServicesResolved(self) -> DBusBool:
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Adapter(self) -> DBusObjectPath:
        return ADAPTER_PATH

    @dbus_property(access=PropertyAccess.READ)
    def Address(self) -> DBusStr:
        return "AA:BB:CC:DD:EE:FF"


class RealDBusDaemon:
    """A private dbus-daemon standing in for the system bus.

    A fake org.bluez exporting an adapter and a connected device is
    served on the daemon by a second bus connection; dbus_fast answers
    GetManagedObjects for the exported objects itself.
    """

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.bluez_bus: MessageBus | None = None

    async def start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.process = subprocess.Popen(
            ["dbus-daemon", "--session", "--nofork", "--print-address=1"],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            assert self.process.stdout is not None
            loop = asyncio.get_running_loop()
            async with async_timeout(10):
                address = (
                    await loop.run_in_executor(None, self.process.stdout.readline)
                ).strip()
            assert address

            # BlueZManager hardcodes BusType.SYSTEM, so the address
            # environment variable is the only seam that redirects it to
            # the private daemon without patching internals
            monkeypatch.setenv("DBUS_SYSTEM_BUS_ADDRESS", address)

            self.bluez_bus = MessageBus(bus_type=BusType.SYSTEM)
            await self.bluez_bus.connect()
            self.bluez_bus.export(ADAPTER_PATH, FakeAdapter1())
            self.bluez_bus.export(DEVICE_PATH, FakeDevice1())
            await self.bluez_bus.request_name(defs.BLUEZ_SERVICE)
        except BaseException:
            self.stop()
            raise

    def stop(self) -> None:
        """Kill the daemon, causing a real socket death for all clients."""
        if self.bluez_bus is not None:
            with contextlib.suppress(Exception):
                self.bluez_bus.disconnect()
            self.bluez_bus = None
        if self.process is not None:
            self.process.kill()
            self.process.wait()
            if self.process.stdout is not None:
                self.process.stdout.close()
            self.process = None


async def test_manager_recovers_from_real_dbus_daemon_death(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    daemon = RealDBusDaemon()
    await daemon.start(monkeypatch)
    manager = BlueZManager()

    try:
        await manager.async_init()
        assert manager.is_connected(DEVICE_PATH) is True

        connected_changes: list[bool] = []
        manager.add_device_watcher(
            DEVICE_PATH, connected_changes.append, noop_characteristic_value_changed
        )
        watcher_task = get_watcher_task(manager)

        # A real socket death, through the real dbus_fast reader
        daemon.stop()
        async with async_timeout(10):
            await watcher_task

        assert connected_changes == [False]
        assert manager.is_connected(DEVICE_PATH) is False
        assert manager._properties == {}  # pyright: ignore[reportPrivateUsage]

        # A new daemon comes up at a new address; async_init recovers
        daemon = RealDBusDaemon()
        await daemon.start(monkeypatch)
        async with async_timeout(10):
            await manager.async_init()

        assert manager.is_connected(DEVICE_PATH) is True
    finally:
        await reap_watcher_task(manager)
        bus = manager._bus  # pyright: ignore[reportPrivateUsage]
        if bus is not None:
            with contextlib.suppress(Exception):
                bus.disconnect()
        daemon.stop()
