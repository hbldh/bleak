#!/usr/bin/env python

"""Tests for `bleak.backends.bluezdbus.utils` package."""

import sys

import pytest

if sys.platform != "linux":
    pytest.skip("skipping linux-only tests", allow_module_level=True)
    assert False  # HACK: work around pyright bug


def test_device_path_from_characteristic_path():
    """Test device_path_from_characteristic_path."""
    from bleak.backends.bluezdbus.utils import (  # pylint: disable=import-outside-toplevel
        device_path_from_characteristic_path,
    )

    assert (
        device_path_from_characteristic_path(
            "/org/bluez/hci0/dev_11_22_33_44_55_66/service000c/char000d"
        )
        == "/org/bluez/hci0/dev_11_22_33_44_55_66"
    )

    assert (
        device_path_from_characteristic_path(
            "/org/bluez/hci10/dev_11_22_33_44_55_66/service000c/char000d"
        )
        == "/org/bluez/hci10/dev_11_22_33_44_55_66"
    )
