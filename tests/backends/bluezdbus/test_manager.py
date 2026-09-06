"""Tests for the BlueZ D-Bus manager handling the message bus disconnecting."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)

from dbus_fast.constants import MessageType
from dbus_fast.message import Message
from dbus_fast.signature import Variant

from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus import manager as manager_module
from bleak.backends.bluezdbus.client import BleakClientBlueZDBus
from bleak.backends.bluezdbus.manager import BlueZManager
from bleak.exc import BleakError

ADAPTER_PATH = "/org/bluez/hci0"
DEVICE_PATH = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"
SERVICE_PATH = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF/service0001"
SECOND_ADAPTER_PATH = "/org/bluez/hci1"
SECOND_DEVICE_PATH = "/org/bluez/hci1/dev_AA_BB_CC_DD_EE_00"
HR_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
UNRELATED_SERVICE_UUID = "0000ffff-0000-1000-8000-00805f9b34fb"


def build_managed_objects(
    services_resolved: bool = True,
    include_second_adapter: bool = False,
) -> dict[str, dict[str, dict[str, Variant]]]:
    managed_objects = {
        ADAPTER_PATH: {
            defs.ADAPTER_INTERFACE: {"Powered": Variant("b", True)},
        },
        DEVICE_PATH: {
            defs.DEVICE_INTERFACE: {
                "Connected": Variant("b", True),
                "ServicesResolved": Variant("b", services_resolved),
                "Adapter": Variant("o", ADAPTER_PATH),
                "Address": Variant("s", "AA:BB:CC:DD:EE:FF"),
                "UUIDs": Variant("as", [HR_SERVICE_UUID]),
            },
        },
        SERVICE_PATH: {
            defs.GATT_SERVICE_INTERFACE: {
                "Device": Variant("o", DEVICE_PATH),
                "UUID": Variant("s", HR_SERVICE_UUID),
            },
        },
    }
    if include_second_adapter:
        managed_objects[SECOND_ADAPTER_PATH] = {
            defs.ADAPTER_INTERFACE: {"Powered": Variant("b", True)},
        }
        managed_objects[SECOND_DEVICE_PATH] = {
            defs.DEVICE_INTERFACE: {
                "Connected": Variant("b", False),
                "ServicesResolved": Variant("b", False),
                "Adapter": Variant("o", SECOND_ADAPTER_PATH),
                "Address": Variant("s", "AA:BB:CC:DD:EE:00"),
            },
        }
    return managed_objects


class FakeMessageBus:
    """A stand-in for the dbus_fast MessageBus with a controllable lifetime."""

    def __init__(self, managed_objects: dict[str, Any]) -> None:
        self._managed_objects = managed_objects
        self.connected = False
        self.handler: Optional[Callable[[Message], None]] = None
        self._disconnect_future: asyncio.Future[None] = (
            asyncio.get_running_loop().create_future()
        )

    async def connect(self) -> None:
        self.connected = True

    def add_message_handler(self, handler: Callable[[Message], None]) -> None:
        self.handler = handler

    async def call(self, msg: Message) -> Message:
        if not self.connected:
            raise EOFError
        return Message(
            message_type=MessageType.METHOD_RETURN,
            reply_serial=1,
            body=[self._managed_objects] if msg.member == "GetManagedObjects" else [],
        )

    def disconnect(self) -> None:
        self.connected = False
        if not self._disconnect_future.done():
            self._disconnect_future.set_result(None)

    async def wait_for_disconnect(self) -> None:
        return await self._disconnect_future

    def die(self, exc: Optional[Exception] = None) -> None:
        """Simulate the socket dying abnormally."""
        self.connected = False
        if not self._disconnect_future.done():
            self._disconnect_future.set_exception(
                exc or EOFError("dbus daemon went away")
            )

    def _finalize(self, err: Optional[Exception]) -> None:
        """Release resources like the real MessageBus does."""
        self.connected = False


class FakeMessageBusFactory:
    """Creates FakeMessageBus instances and records them."""

    def __init__(self, managed_objects: dict[str, Any]) -> None:
        self.managed_objects = managed_objects
        self.instances: list[FakeMessageBus] = []

    def __call__(self, *args: Any, **kwargs: Any) -> FakeMessageBus:
        bus = FakeMessageBus(self.managed_objects)
        self.instances.append(bus)
        return bus


def noop_characteristic_value_changed(char_path: str, value: bytes) -> None:
    pass


def get_watcher_task(manager: BlueZManager) -> "asyncio.Task[None]":
    task = manager._bus_watcher_task  # pyright: ignore[reportPrivateUsage]
    assert task is not None
    return task


MakeManager = Callable[..., Awaitable[tuple[BlueZManager, FakeMessageBusFactory]]]


@pytest.fixture
async def make_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[MakeManager]:
    """Create initialized managers and reap their watcher tasks at teardown."""
    managers: list[BlueZManager] = []

    async def _make(
        managed_objects: Optional[dict[str, Any]] = None,
    ) -> tuple[BlueZManager, FakeMessageBusFactory]:
        factory = FakeMessageBusFactory(managed_objects or build_managed_objects())
        monkeypatch.setattr(manager_module, "MessageBus", factory)
        manager = BlueZManager()
        await manager.async_init()
        managers.append(manager)
        return manager, factory

    yield _make

    for manager in managers:
        task = manager._bus_watcher_task  # pyright: ignore[reportPrivateUsage]
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def test_bus_death_resets_state_and_notifies_watchers(
    make_manager: MakeManager,
) -> None:
    manager, factory = await make_manager()
    bus = factory.instances[0]

    connected_changes: list[bool] = []
    manager.add_device_watcher(
        DEVICE_PATH, connected_changes.append, noop_characteristic_value_changed
    )

    assert manager.is_connected(DEVICE_PATH) is True

    bus.die()
    await get_watcher_task(manager)

    assert connected_changes == [False]
    assert manager._properties == {}  # pyright: ignore[reportPrivateUsage]
    assert manager._services_cache == {}  # pyright: ignore[reportPrivateUsage]
    assert manager.is_connected(DEVICE_PATH) is False


async def test_bus_death_unblocks_pending_service_discovery(
    make_manager: MakeManager,
) -> None:
    manager, factory = await make_manager(
        build_managed_objects(services_resolved=False)
    )
    bus = factory.instances[0]

    discovery_task = asyncio.create_task(
        manager._wait_for_services_discovery(  # pyright: ignore[reportPrivateUsage]
            DEVICE_PATH
        )
    )
    await asyncio.sleep(0)
    assert not discovery_task.done()

    bus.die()
    await get_watcher_task(manager)

    with pytest.raises(BleakError, match="device disconnected"):
        await discovery_task


async def test_async_init_recovers_after_bus_death(
    make_manager: MakeManager,
) -> None:
    manager, factory = await make_manager()
    bus = factory.instances[0]

    bus.die()
    dead_watcher_task = get_watcher_task(manager)
    await dead_watcher_task
    assert manager._properties == {}  # pyright: ignore[reportPrivateUsage]

    await manager.async_init()

    assert len(factory.instances) == 2
    assert manager._bus is factory.instances[1]  # pyright: ignore[reportPrivateUsage]
    assert DEVICE_PATH in manager._properties  # pyright: ignore[reportPrivateUsage]
    assert manager.is_connected(DEVICE_PATH) is True
    assert get_watcher_task(manager) is not dead_watcher_task


async def test_reinit_does_not_notify_watchers(
    make_manager: MakeManager,
) -> None:
    manager, factory = await make_manager()
    bus = factory.instances[0]

    connected_changes: list[bool] = []
    manager.add_device_watcher(
        DEVICE_PATH, connected_changes.append, noop_characteristic_value_changed
    )

    # The bus is no longer connected but the socket has not errored yet;
    # async_init replaces it and disconnects it without firing watchers.
    bus.connected = False
    superseded_watcher_task = get_watcher_task(manager)
    await manager.async_init()
    with contextlib.suppress(asyncio.CancelledError):
        await superseded_watcher_task

    assert manager._bus is factory.instances[1]  # pyright: ignore[reportPrivateUsage]
    assert connected_changes == []
    assert manager.is_connected(DEVICE_PATH) is True


async def test_bus_death_callback_exception_does_not_stop_notifications(
    make_manager: MakeManager,
) -> None:
    manager, factory = await make_manager(
        build_managed_objects(include_second_adapter=True)
    )
    bus = factory.instances[0]

    def raising_connected_changed(connected: bool) -> None:
        raise RuntimeError("bad callback")

    connected_changes: list[bool] = []
    manager.add_device_watcher(
        DEVICE_PATH, raising_connected_changed, noop_characteristic_value_changed
    )
    manager.add_device_watcher(
        DEVICE_PATH, connected_changes.append, noop_characteristic_value_changed
    )

    removed_paths: list[str] = []
    manager._device_removed_callbacks.append(  # pyright: ignore[reportPrivateUsage]
        manager_module.DeviceRemovedCallbackAndState(removed_paths.append, ADAPTER_PATH)
    )

    bus.die()
    await get_watcher_task(manager)

    # The raising watcher does not prevent the other notifications, and
    # the device on the other adapter does not match the removed callback
    assert connected_changes == [False]
    assert removed_paths == [DEVICE_PATH]
    assert manager.is_connected(DEVICE_PATH) is False


async def test_watcher_ignores_superseded_bus(
    make_manager: MakeManager,
) -> None:
    manager, factory = await make_manager()
    bus = factory.instances[0]
    watcher_task = get_watcher_task(manager)

    # Simulate async_init having replaced the bus without the watcher
    # task being cancelled yet
    manager._bus = FakeMessageBus({})  # type: ignore[assignment] # pyright: ignore[reportPrivateUsage]
    bus.die()
    await watcher_task

    assert manager.is_connected(DEVICE_PATH) is True


async def test_global_manager_cleans_up_closed_loops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_loop = asyncio.new_event_loop()
    closed_loop.close()
    stale_manager = MagicMock()
    never_started_loop = asyncio.new_event_loop()
    never_started_loop.close()
    never_started_manager = MagicMock()
    never_started_manager._bus_watcher_task = None
    never_started_manager._bus = None
    instances = manager_module._global_instances  # pyright: ignore[reportPrivateUsage]
    instances[closed_loop] = stale_manager
    instances[never_started_loop] = never_started_manager

    factory = FakeMessageBusFactory(build_managed_objects())
    monkeypatch.setattr(manager_module, "MessageBus", factory)
    manager: Optional[BlueZManager] = None
    try:
        manager = await manager_module.get_global_bluez_manager()

        assert closed_loop not in instances
        assert never_started_loop not in instances
        stale_manager._bus_watcher_task.cancel.assert_called_once_with()
        stale_manager._bus._finalize.assert_called_once_with(None)
    finally:
        instances.pop(asyncio.get_running_loop(), None)
        if manager is not None:
            task = get_watcher_task(manager)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def test_parse_msg_connected_change_notifies_watchers(
    make_manager: MakeManager,
) -> None:
    manager, factory = await make_manager()
    bus = factory.instances[0]

    connected_changes: list[bool] = []
    manager.add_device_watcher(
        DEVICE_PATH, connected_changes.append, noop_characteristic_value_changed
    )
    disconnected_wait_task = asyncio.create_task(
        manager._wait_condition(  # pyright: ignore[reportPrivateUsage]
            DEVICE_PATH, "Connected", False
        )
    )
    await asyncio.sleep(0)

    assert bus.handler is not None
    bus.handler(
        Message(
            message_type=MessageType.SIGNAL,
            path=DEVICE_PATH,
            interface=defs.PROPERTIES_INTERFACE,
            member="PropertiesChanged",
            signature="sa{sv}as",
            body=[defs.DEVICE_INTERFACE, {"Connected": Variant("b", False)}, []],
        )
    )

    assert connected_changes == [False]
    assert manager.is_connected(DEVICE_PATH) is False
    await asyncio.wait_for(disconnected_wait_task, timeout=1)


async def test_get_connected_devices(make_manager: MakeManager) -> None:
    manager, _ = await make_manager(build_managed_objects(include_second_adapter=True))

    matches = manager.get_connected_devices(ADAPTER_PATH, frozenset({HR_SERVICE_UUID}))
    assert [path for path, _ in matches] == [DEVICE_PATH]

    no_matches = manager.get_connected_devices(
        ADAPTER_PATH, frozenset({UNRELATED_SERVICE_UUID})
    )
    assert no_matches == []


async def test_watcher_logs_unexpected_handler_error(
    make_manager: MakeManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, factory = await make_manager()
    bus = factory.instances[0]

    def raising_handler() -> None:
        raise RuntimeError("unexpected handler failure")

    monkeypatch.setattr(manager, "_handle_bus_disconnect", raising_handler)
    bus.die()

    # The watcher task logs the error instead of raising it
    await get_watcher_task(manager)


async def test_global_manager_cleans_up_closed_loop_with_real_watcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A watcher task left on a closed loop must not break the accessor."""
    factory = FakeMessageBusFactory(build_managed_objects())
    monkeypatch.setattr(manager_module, "MessageBus", factory)

    def init_manager_on_own_loop() -> tuple[BlueZManager, asyncio.AbstractEventLoop]:
        own_loop = asyncio.new_event_loop()
        stale_manager = BlueZManager()
        own_loop.run_until_complete(stale_manager.async_init())
        own_loop.close()
        return stale_manager, own_loop

    loop = asyncio.get_running_loop()
    stale_manager, closed_loop = await loop.run_in_executor(
        None, init_manager_on_own_loop
    )
    assert not get_watcher_task(stale_manager).done()
    instances = manager_module._global_instances  # pyright: ignore[reportPrivateUsage]
    instances[closed_loop] = stale_manager

    manager: Optional[BlueZManager] = None
    try:
        # Must not raise even though the stale watcher task can only be
        # cancelled through its closed loop
        manager = await manager_module.get_global_bluez_manager()

        assert closed_loop not in instances
    finally:
        instances.pop(loop, None)
        if manager is not None:
            task = get_watcher_task(manager)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


class ExplodingFakeMessageBus(FakeMessageBus):
    """A bus whose teardown raises an unexpected error."""

    def disconnect(self) -> None:
        raise RuntimeError("unexpected teardown failure")


async def test_client_disconnect_with_unexpected_teardown_error() -> None:
    client = BleakClientBlueZDBus("AA:BB:CC:DD:EE:FF", bluez={}, timeout=10)
    client._device_path = DEVICE_PATH  # pyright: ignore[reportPrivateUsage]
    client._bus = ExplodingFakeMessageBus({})  # type: ignore[assignment] # pyright: ignore[reportPrivateUsage]

    await client.disconnect()

    assert client._bus is None  # pyright: ignore[reportPrivateUsage]


async def test_client_disconnect_with_dead_bus() -> None:
    client = BleakClientBlueZDBus("AA:BB:CC:DD:EE:FF", bluez={}, timeout=10)
    client._device_path = DEVICE_PATH  # pyright: ignore[reportPrivateUsage]

    dead_bus = FakeMessageBus({})
    dead_bus.die()
    client._bus = dead_bus  # type: ignore[assignment] # pyright: ignore[reportPrivateUsage]
    client._is_connected = True  # pyright: ignore[reportPrivateUsage]

    await client.disconnect()

    assert client._bus is None  # pyright: ignore[reportPrivateUsage]
    assert client.is_connected is False
    assert client.services is None
