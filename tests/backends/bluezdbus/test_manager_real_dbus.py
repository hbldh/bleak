"""Tests for BlueZManager bus loss handling against a real dbus-daemon."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import contextlib
import shutil
import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

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
from bleak.backends.bluezdbus import manager as manager_module
from bleak.backends.bluezdbus.manager import BlueZManager

from .conftest import (
    ADAPTER_PATH,
    DEVICE_ADDRESS,
    DEVICE_PATH,
    get_watcher_task,
    init_manager_on_closed_loop,
    release_manager,
    watch_connected,
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
        self.connected = True

    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> DBusBool:
        return self.connected

    def disconnect(self) -> None:
        """Signals the device disconnecting over the wire."""
        self.connected = False
        self.emit_properties_changed({"Connected": False})

    @dbus_property(access=PropertyAccess.READ)
    def ServicesResolved(self) -> DBusBool:
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Adapter(self) -> DBusObjectPath:
        return ADAPTER_PATH

    @dbus_property(access=PropertyAccess.READ)
    def Address(self) -> DBusStr:
        return DEVICE_ADDRESS


# A minimal bus configuration so the test does not depend on the
# system's session bus setup (e.g. launchd on macOS).
BUS_CONFIG = f"""\
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir={tempfile.gettempdir()}</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""


class RealDBusDaemon:
    """A private dbus-daemon standing in for the system bus.

    A fake org.bluez exporting an adapter and a connected device is
    served on the daemon by a second bus connection; dbus_fast answers
    GetManagedObjects for the exported objects itself.
    """

    def __init__(self) -> None:
        self.process: asyncio.subprocess.Process | None = None
        self.bluez_bus: MessageBus | None = None
        self.device = FakeDevice1()

    async def start(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config_file = tmp_path / "bus.conf"
        config_file.write_text(BUS_CONFIG)
        self.process = await asyncio.create_subprocess_exec(
            "dbus-daemon",
            f"--config-file={config_file}",
            "--nofork",
            "--print-address=1",
            stdout=asyncio.subprocess.PIPE,
        )
        try:
            assert self.process.stdout is not None
            async with async_timeout(10):
                address = (await self.process.stdout.readline()).decode().strip()
            assert address

            # BlueZManager hardcodes BusType.SYSTEM, so the address
            # environment variable is the only seam that redirects it to
            # the private daemon without patching internals
            monkeypatch.setenv("DBUS_SYSTEM_BUS_ADDRESS", address)

            self.bluez_bus = MessageBus(bus_type=BusType.SYSTEM)
            await self.bluez_bus.connect()
            self.bluez_bus.export(ADAPTER_PATH, FakeAdapter1())
            self.bluez_bus.export(DEVICE_PATH, self.device)
            await self.bluez_bus.request_name(defs.BLUEZ_SERVICE)
        except BaseException:
            await self.stop()
            raise

    def kill(self) -> None:
        """Kill the daemon, causing a real socket death for all clients."""
        if self.bluez_bus is not None:
            with contextlib.suppress(Exception):
                self.bluez_bus.disconnect()
            self.bluez_bus = None
        if self.process is not None and self.process.returncode is None:
            self.process.kill()

    async def stop(self) -> None:
        """Kill the daemon and reap it."""
        self.kill()
        if self.process is not None:
            await self.process.wait()
            self.process = None


StartDaemon = Callable[[], Awaitable[RealDBusDaemon]]


@pytest.fixture
async def start_daemon(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncIterator[StartDaemon]:
    """Starts daemons and stops any still running at teardown."""
    daemons: list[RealDBusDaemon] = []

    async def _start() -> RealDBusDaemon:
        daemon = RealDBusDaemon()
        await daemon.start(monkeypatch, tmp_path)
        daemons.append(daemon)
        return daemon

    yield _start

    for daemon in daemons:
        await daemon.stop()


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
