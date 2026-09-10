"""Regression test for <https://github.com/hbldh/bleak/issues/2021>."""

import logging
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

LOGGER = "bleak.backends.bluezdbus.manager"


def _on_advertisement(path: str, props: Device1) -> None:
    pass


def _on_removed(path: str) -> None:
    pass


_ADV: AdvertisementCallback = _on_advertisement
_REMOVED: DeviceRemovedCallback = _on_removed


class FakeBus:
    """
    Answers every call with a method return, except StopDiscovery, which is
    answered from ``stop_errors`` in order (``None`` means success) and with
    success once that list is used up.
    """

    def __init__(self, stop_errors: "list[str | None]") -> None:
        self.stop_errors = list(stop_errors)
        self.members: "list[str | None]" = []

    async def call(self, msg: Message) -> Message:
        # outgoing messages carry serial 0 until a real bus assigns one, so
        # replies are built explicitly rather than derived from the request
        self.members.append(msg.member)
        if msg.member == "StopDiscovery" and self.stop_errors:
            error = self.stop_errors.pop(0)
            if error is not None:
                return Message(
                    message_type=MessageType.ERROR,
                    reply_serial=1,
                    error_name=error,
                    signature="s",
                    body=["Operation already in progress"],
                )
        return Message(message_type=MessageType.METHOD_RETURN, reply_serial=1)


def make_manager(stop_errors: "list[str | None]") -> "tuple[BlueZManager, FakeBus]":
    manager = BlueZManager()
    bus = FakeBus(stop_errors)
    manager._bus = bus  # type: ignore[assignment]
    manager._properties[ADAPTER_PATH] = {defs.ADAPTER_INTERFACE: {}}
    return manager, bus


async def _scan_and_stop(manager: BlueZManager) -> None:
    stop = await manager.active_scan(ADAPTER_PATH, NO_FILTERS, _ADV, _REMOVED)
    await stop()


def _records(caplog: pytest.LogCaptureFixture, level: int) -> "list[str]":
    return [r.getMessage() for r in caplog.records if r.levelno == level]


async def test_stop_tolerates_in_progress(caplog: pytest.LogCaptureFixture) -> None:
    """
    BlueZ answers StopDiscovery with InProgress when the kernel has already
    stopped scanning; the discovery session is gone by then, so stop() must
    return normally, leave the manager's bookkeeping clean, and leave a
    record in the log.
    """
    manager, bus = make_manager([defs.BLUEZ_ERROR_IN_PROGRESS])

    with caplog.at_level(logging.INFO, logger=LOGGER):
        await _scan_and_stop(manager)

    assert bus.members == ["SetDiscoveryFilter", "StartDiscovery", "StopDiscovery"]
    assert manager._advertisement_callbacks[ADAPTER_PATH] == []
    assert manager._device_removed_callbacks == []
    assert any(
        "InProgress" in m and ADAPTER_PATH in m for m in _records(caplog, logging.INFO)
    )
    assert not _records(caplog, logging.WARNING)


async def test_second_consecutive_in_progress_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    A single rejection is a race with the kernel's scan timeout and the next
    stop succeeds. Two in a row means bluetoothd's discovery state is stuck
    and no scan on the adapter reaches the kernel, so the second one must be
    reported as an error, with a warning that says what to do.
    """
    manager, bus = make_manager(
        [defs.BLUEZ_ERROR_IN_PROGRESS, defs.BLUEZ_ERROR_IN_PROGRESS]
    )

    with caplog.at_level(logging.INFO, logger=LOGGER):
        await _scan_and_stop(manager)
        with pytest.raises(BleakDBusError) as info:
            await _scan_and_stop(manager)

    assert info.value.dbus_error == defs.BLUEZ_ERROR_IN_PROGRESS
    assert bus.members.count("StopDiscovery") == 2
    # the callbacks were still removed before the failing stop
    assert manager._advertisement_callbacks[ADAPTER_PATH] == []
    assert manager._device_removed_callbacks == []
    warnings = _records(caplog, logging.WARNING)
    assert len(warnings) == 1
    assert "twice in a row" in warnings[0] and ADAPTER_PATH in warnings[0]


async def test_a_clean_stop_resets_the_count(caplog: pytest.LogCaptureFixture) -> None:
    """A successful stop between two rejections means they were two separate
    races, not a stuck adapter; neither may raise."""
    manager, bus = make_manager(
        [defs.BLUEZ_ERROR_IN_PROGRESS, None, defs.BLUEZ_ERROR_IN_PROGRESS]
    )

    with caplog.at_level(logging.INFO, logger=LOGGER):
        await _scan_and_stop(manager)
        await _scan_and_stop(manager)
        await _scan_and_stop(manager)

    assert bus.members.count("StopDiscovery") == 3
    # only the successful stop goes on to reset the discovery filter
    assert bus.members.count("SetDiscoveryFilter") == 3 + 1
    assert len(_records(caplog, logging.INFO)) == 2
    assert not _records(caplog, logging.WARNING)


async def test_stop_still_raises_other_errors() -> None:
    manager, _ = make_manager([defs.BLUEZ_ERROR_FAILED])

    stop = await manager.active_scan(ADAPTER_PATH, NO_FILTERS, _ADV, _REMOVED)
    with pytest.raises(BleakDBusError) as info:
        await stop()

    assert info.value.dbus_error == defs.BLUEZ_ERROR_FAILED
