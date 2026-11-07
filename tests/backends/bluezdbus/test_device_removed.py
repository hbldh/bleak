"""Tests for BlueZManager device removed callbacks."""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)

from dbus_fast.constants import MessageType
from dbus_fast.message import Message

from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.manager import BlueZManager, DeviceRemovedCallbackAndState

WATCHED_DEVICE_PATH = "/org/bluez/hci1/dev_AA_BB_CC_DD_EE_01"
OTHER_DEVICE_PATH = "/org/bluez/hci10/dev_AA_BB_CC_DD_EE_10"


def test_device_removed_callbacks_match_only_the_watched_adapter() -> None:
    manager = BlueZManager()
    removed_paths: list[str] = []
    manager._device_removed_callbacks.append(  # pyright: ignore[reportPrivateUsage]
        DeviceRemovedCallbackAndState(removed_paths.append, "/org/bluez/hci1")
    )

    for device_path in (OTHER_DEVICE_PATH, WATCHED_DEVICE_PATH):
        manager._parse_msg(  # pyright: ignore[reportPrivateUsage]
            Message(
                message_type=MessageType.SIGNAL,
                path="/",
                interface=defs.OBJECT_MANAGER_INTERFACE,
                member="InterfacesRemoved",
                signature="oas",
                body=[device_path, [defs.DEVICE_INTERFACE]],
            )
        )

    # the adapter path is a prefix of hci10, which must not match
    assert removed_paths == [WATCHED_DEVICE_PATH]
