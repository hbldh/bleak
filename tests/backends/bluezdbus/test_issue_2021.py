"""Regression test for <https://github.com/hbldh/bleak/issues/2021>."""

import sys

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)
    assert False  # HACK: work around pyright bug

from dbus_fast import Message, MessageType, Variant

from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.manager import (
    AdvertisementCallback,
    BlueZManager,
    Device1,
    DeviceRemovedCallback,
)
from bleak.exc import BleakDBusError

ADAPTER_PATH = "/org/bluez/hci0"

NO_FILTERS: dict[str, Variant] = {}


def _on_advertisement(path: str, props: Device1) -> None:
    pass


def _on_removed(path: str) -> None:
    pass


_ADV: AdvertisementCallback = _on_advertisement
_REMOVED: DeviceRemovedCallback = _on_removed


class FakeBus:
    """Answers every call with a method return, except StopDiscovery."""

    def __init__(self, stop_error: "str | None") -> None:
        self.stop_error = stop_error
        self.members: "list[str | None]" = []

    async def call(self, msg: Message) -> Message:
        # outgoing messages carry serial 0 until a real bus assigns one, so
        # replies are built explicitly rather than derived from the request
        self.members.append(msg.member)
        if msg.member == "StopDiscovery" and self.stop_error is not None:
            return Message(
                message_type=MessageType.ERROR,
                reply_serial=1,
                error_name=self.stop_error,
                signature="s",
                body=["Operation already in progress"],
            )
        return Message(message_type=MessageType.METHOD_RETURN, reply_serial=1)


def make_manager(stop_error: "str | None") -> "tuple[BlueZManager, FakeBus]":
    manager = BlueZManager()
    bus = FakeBus(stop_error)
    manager._bus = bus  # type: ignore[assignment]
    manager._properties[ADAPTER_PATH] = {defs.ADAPTER_INTERFACE: {}}
    return manager, bus


async def test_stop_tolerates_in_progress() -> None:
    """
    BlueZ answers StopDiscovery with InProgress when the kernel has already
    stopped scanning; the discovery session is gone by then, so stop() must
    return normally and leave the manager's bookkeeping clean.
    """
    manager, bus = make_manager(defs.BLUEZ_ERROR_IN_PROGRESS)

    stop = await manager.active_scan(ADAPTER_PATH, NO_FILTERS, _ADV, _REMOVED)
    await stop()

    assert bus.members == ["SetDiscoveryFilter", "StartDiscovery", "StopDiscovery"]
    assert manager._advertisement_callbacks[ADAPTER_PATH] == []
    assert manager._device_removed_callbacks == []


async def test_stop_still_raises_other_errors() -> None:
    manager, _ = make_manager(defs.BLUEZ_ERROR_FAILED)

    stop = await manager.active_scan(ADAPTER_PATH, NO_FILTERS, _ADV, _REMOVED)
    with pytest.raises(BleakDBusError) as info:
        await stop()

    assert info.value.dbus_error == defs.BLUEZ_ERROR_FAILED
