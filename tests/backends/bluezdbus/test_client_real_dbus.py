"""Tests for BleakClient.disconnect() against a real dbus-daemon with a fake BlueZ."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
from collections.abc import Callable
from typing import Optional

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)

from dbus_fast.aio.message_bus import MessageBus

from bleak import BleakClient
from bleak.backends.bluezdbus.client import BleakClientBlueZDBus
from bleak.backends.bluezdbus.manager import BlueZManager, get_global_bluez_manager
from bleak.backends.bluezdbus.version import BlueZFeatures
from bleak.backends.device import BLEDevice
from bleak.exc import BleakDBusError

from .conftest import DEVICE_ADDRESS, DEVICE_PATH
from .fake_bluez import StartDaemon

# long enough for the client's own calls, short enough to keep the test fast
REPLY_TIMEOUT_MS = 500


@pytest.fixture(autouse=True)
def skip_bluez_version_check(monkeypatch: pytest.MonkeyPatch) -> None:
    # the check runs bluetoothctl, which is not part of the fake BlueZ
    monkeypatch.setattr(BlueZFeatures, "checked_bluez_version", True)
    monkeypatch.setattr(BlueZFeatures, "supported_version", True)


async def connect(
    disconnected_callback: Callable[[BleakClient], None],
) -> tuple[BleakClient, MessageBus]:
    """Connects to the fake device and returns the client's own bus."""
    client = BleakClient(
        BLEDevice(DEVICE_ADDRESS, None, {"path": DEVICE_PATH, "props": {}}),
        disconnected_callback=disconnected_callback,
    )
    await client.connect()

    backend = client._backend  # pyright: ignore[reportPrivateUsage]
    assert isinstance(backend, BleakClientBlueZDBus)
    bus = backend._bus  # pyright: ignore[reportPrivateUsage]
    assert bus is not None

    return client, bus


async def assert_torn_down(client: BleakClient, bus: MessageBus) -> None:
    # the client's bus is closed and no watcher is left that could notify
    # this client about a later connection
    assert bus.connected is False
    manager = await get_global_bluez_manager()
    watchers = manager._device_watchers  # pyright: ignore[reportPrivateUsage]
    assert not watchers.get(DEVICE_PATH)
    assert client.is_connected is False

    backend = client._backend  # pyright: ignore[reportPrivateUsage]
    assert isinstance(backend, BleakClientBlueZDBus)
    assert backend.services is None
    monitor = backend._disconnect_monitor_event  # pyright: ignore[reportPrivateUsage]
    assert monitor is None


async def test_disconnect(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
) -> None:
    daemon = await start_daemon()
    disconnections: list[BleakClient] = []
    client, bus = await connect(disconnections.append)

    await client.disconnect()

    assert daemon.device.calls == ["Disconnect"]
    await assert_torn_down(client, bus)
    assert disconnections == [client]


async def test_disconnect_without_reply_tears_down(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
) -> None:
    """
    bluetoothd holds Disconnect when the kernel refuses it, and a bus daemon
    with a reply_timeout answers NoReply. The client must still close its
    bus, remove its watcher and notify once.
    """
    daemon = await start_daemon(reply_timeout_ms=REPLY_TIMEOUT_MS)
    daemon.device.on_disconnect = "no-reply"
    disconnections: list[BleakClient] = []
    client, bus = await connect(disconnections.append)

    with pytest.raises(BleakDBusError) as e:
        await client.disconnect()

    assert e.value.dbus_error == "org.freedesktop.DBus.Error.NoReply"
    await assert_torn_down(client, bus)
    assert disconnections == [client]


async def test_canceled_disconnect_tears_down(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
) -> None:
    """
    dbus-daemon never times out a call by default, so a Disconnect that
    bluetoothd holds keeps disconnect() waiting until the application gives
    up. Canceling it must still close the bus, remove the watcher and notify
    once.
    """
    daemon = await start_daemon()
    daemon.device.on_disconnect = "no-reply"
    disconnections: list[BleakClient] = []
    client, bus = await connect(disconnections.append)

    task = asyncio.create_task(client.disconnect())

    # cancel only once BlueZ is holding the call
    async with asyncio.timeout(10):
        while daemon.device.calls != ["Disconnect"]:
            await asyncio.sleep(0.01)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await assert_torn_down(client, bus)
    assert disconnections == [client]


async def test_concurrent_disconnect_returns_when_first_is_canceled(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
) -> None:
    """A second disconnect() waiting on the first one returns once it is torn down."""
    daemon = await start_daemon()
    daemon.device.on_disconnect = "no-reply"
    disconnections: list[BleakClient] = []
    client, bus = await connect(disconnections.append)

    first = asyncio.create_task(client.disconnect())

    async with asyncio.timeout(10):
        while daemon.device.calls != ["Disconnect"]:
            await asyncio.sleep(0.01)

    second = asyncio.create_task(client.disconnect())
    # the second call has no await before it starts waiting on the first
    await asyncio.sleep(0)

    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first

    async with asyncio.timeout(1):
        await second

    assert daemon.device.calls == ["Disconnect"]
    await assert_torn_down(client, bus)
    assert disconnections == [client]


async def test_disconnect_timeout_tears_down(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Disconnect is answered before "Connected" changes, as BlueZ 5.72 does for
    the first bearer of a dual-mode device. Here it never changes, so the
    wait times out.
    """
    daemon = await start_daemon()
    daemon.device.on_disconnect = "reply"
    disconnections: list[BleakClient] = []
    client, bus = await connect(disconnections.append)

    real_timeout = asyncio.timeout

    def short_timeout(delay: Optional[float]) -> asyncio.Timeout:
        return real_timeout(0.1)

    # disconnect() waits 10 s for "Connected" to change
    with monkeypatch.context() as m:
        m.setattr(asyncio, "timeout", short_timeout)

        with pytest.raises(TimeoutError):
            await client.disconnect()

    await assert_torn_down(client, bus)
    assert disconnections == [client]


async def test_reconnect_after_failed_disconnect(
    start_daemon: StartDaemon,
    global_instances: dict[asyncio.AbstractEventLoop, BlueZManager],
) -> None:
    """
    After a failed disconnect the link may still be up. Connecting again
    adopts it, and its later disconnection is reported exactly once.
    """
    daemon = await start_daemon(reply_timeout_ms=REPLY_TIMEOUT_MS)
    daemon.device.on_disconnect = "no-reply"
    disconnections: list[BleakClient] = []
    client, _ = await connect(disconnections.append)

    with pytest.raises(BleakDBusError):
        await client.disconnect()

    # BlueZ still reports the device connected, so connect() adopts the link
    await client.connect()
    backend = client._backend  # pyright: ignore[reportPrivateUsage]
    assert isinstance(backend, BleakClientBlueZDBus)
    bus = backend._bus  # pyright: ignore[reportPrivateUsage]
    assert bus is not None
    before = len(disconnections)

    # the device goes away on its own
    daemon.device.disconnect()
    async with asyncio.timeout(10):
        while len(disconnections) == before:
            await asyncio.sleep(0.01)

    # the manager calls every watcher of the device from the same signal, so
    # a watcher left over from the first connection would show up here too
    assert len(disconnections) == before + 1

    await client.disconnect()
    await assert_torn_down(client, bus)
