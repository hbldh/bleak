"""Tests for the BlueZ D-Bus scanner backend."""

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)

from bleak.args.bluez import OrPattern
from bleak.assigned_numbers import AdvertisementDataType
from bleak.backends.bluezdbus.scanner import BleakScannerBlueZDBus


@pytest.mark.parametrize(
    "or_patterns",
    [
        [OrPattern(0, AdvertisementDataType.FLAGS, b"\x06")],
        [(0, AdvertisementDataType.FLAGS, b"\x06")],
        ((0, AdvertisementDataType.FLAGS, b"\x06"),),
    ],
    ids=["named_tuple", "tuple", "tuple_of_tuples"],
)
def test_passive_scan_accepts_valid_or_patterns(or_patterns: Any) -> None:
    BleakScannerBlueZDBus(None, None, "passive", bluez={"or_patterns": or_patterns})


@pytest.mark.parametrize(
    "or_patterns",
    [
        [(0, "flags", b"\x06")],
        [(0, AdvertisementDataType.FLAGS, "\x06")],
        [(0, AdvertisementDataType.FLAGS)],
        [(256, AdvertisementDataType.FLAGS, b"\x06")],
    ],
    ids=["str_ad_type", "str_content", "missing_content", "start_out_of_range"],
)
def test_passive_scan_rejects_invalid_or_patterns(or_patterns: Any) -> None:
    # Otherwise dbus-fast would only log an error when the monitor is exported
    # and BlueZ would never see the patterns.
    with pytest.raises(ValueError, match="invalid bluez or_patterns"):
        BleakScannerBlueZDBus(None, None, "passive", bluez={"or_patterns": or_patterns})
