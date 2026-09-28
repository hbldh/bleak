"""Regression test for <https://github.com/hbldh/bleak/issues/2021>."""

import logging
import sys
from typing import Any

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

FILTERS: dict[str, Variant] = {"Transport": Variant("s", "le")}

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
        self.calls: "list[tuple[str | None, list[Any]]]" = []

    async def call(self, msg: Message) -> Message:
        # outgoing messages carry serial 0 until a real bus assigns one, so
        # replies are built explicitly rather than derived from the request
        self.calls.append((msg.member, msg.body))
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

    @property
    def members(self) -> "list[str | None]":
        return [member for member, _ in self.calls]


def make_manager(stop_errors: "list[str | None]") -> "tuple[BlueZManager, FakeBus]":
    manager = BlueZManager()
    bus = FakeBus(stop_errors)
    manager._bus = bus  # type: ignore[assignment]
    properties = manager._properties  # pyright: ignore[reportPrivateUsage]
    properties[ADAPTER_PATH] = {defs.ADAPTER_INTERFACE: {}}
    return manager, bus


async def _scan_and_stop(manager: BlueZManager) -> None:
    stop = await manager.active_scan(ADAPTER_PATH, FILTERS, _ADV, _REMOVED)
    await stop()


def _assert_callbacks_removed(manager: BlueZManager) -> None:
    """stop() removes the session's callbacks before it talks to BlueZ, so
    they must be gone whether or not the StopDiscovery call succeeded."""
    adv = manager._advertisement_callbacks  # pyright: ignore[reportPrivateUsage]
    removed = manager._device_removed_callbacks  # pyright: ignore[reportPrivateUsage]
    assert adv[ADAPTER_PATH] == []
    assert removed == []


def _records(caplog: pytest.LogCaptureFixture, level: int) -> "list[str]":
    return [r.getMessage() for r in caplog.records if r.levelno == level]


async def test_stop_tolerates_in_progress_when_a_probe_scan_stops_cleanly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    BlueZ answers StopDiscovery with InProgress when the kernel has already
    stopped scanning; the discovery session is gone by then. stop() probes
    the adapter with a start/stop pair, and when that stops cleanly it
    returns normally, clears the filters and leaves a record in the log.
    """
    manager, bus = make_manager([defs.BLUEZ_ERROR_IN_PROGRESS, None])

    with caplog.at_level(logging.INFO, logger=LOGGER):
        await _scan_and_stop(manager)

    assert bus.calls == [
        ("SetDiscoveryFilter", [FILTERS]),
        ("StartDiscovery", []),
        ("StopDiscovery", []),
        # the probe uses the same filters ...
        ("SetDiscoveryFilter", [FILTERS]),
        ("StartDiscovery", []),
        ("StopDiscovery", []),
        # ... and the filters are cleared once it has stopped
        ("SetDiscoveryFilter", [{}]),
    ]
    _assert_callbacks_removed(manager)
    assert any(
        "InProgress" in m and ADAPTER_PATH in m for m in _records(caplog, logging.INFO)
    )
    assert not _records(caplog, logging.WARNING)


async def test_stop_raises_when_the_probe_scan_cannot_be_stopped_either(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    When the probe's stop is rejected as well, bluetoothd's discovery state
    is stuck and no scan on the adapter reaches the kernel. The original
    error is raised, with a warning that says what to do.
    """
    manager, bus = make_manager(
        [defs.BLUEZ_ERROR_IN_PROGRESS, defs.BLUEZ_ERROR_IN_PROGRESS]
    )

    with caplog.at_level(logging.INFO, logger=LOGGER):
        with pytest.raises(BleakDBusError) as info:
            await _scan_and_stop(manager)

    assert info.value.dbus_error == defs.BLUEZ_ERROR_IN_PROGRESS
    assert bus.members.count("StopDiscovery") == 2
    # nothing stopped, so the filters are not cleared
    assert bus.calls[-1] == ("StopDiscovery", [])
    _assert_callbacks_removed(manager)
    warnings = _records(caplog, logging.WARNING)
    assert len(warnings) == 1
    assert "probe scan" in warnings[0] and ADAPTER_PATH in warnings[0]


async def test_stop_tolerates_not_ready_without_probing() -> None:
    """A powered-off adapter has nothing to stop and no filters to clear."""
    manager, bus = make_manager([defs.BLUEZ_ERROR_NOT_READY])

    await _scan_and_stop(manager)

    assert bus.members == ["SetDiscoveryFilter", "StartDiscovery", "StopDiscovery"]
    _assert_callbacks_removed(manager)


async def test_stop_still_raises_other_errors() -> None:
    manager, bus = make_manager([defs.BLUEZ_ERROR_FAILED])

    with pytest.raises(BleakDBusError) as info:
        await _scan_and_stop(manager)

    assert info.value.dbus_error == defs.BLUEZ_ERROR_FAILED
    assert bus.members.count("StopDiscovery") == 1
    _assert_callbacks_removed(manager)
