#!/usr/bin/env python

"""Tests for `bleak.backends.bluezdbus.utils` package."""

from bleak.backends.bluezdbus.utils import device_path_from_characteristic_path


def test_device_path_from_characteristic_path():
    """Test device_path_from_characteristic_path."""
    assert (
        device_path_from_characteristic_path(
            "/org/bluez/hci0/dev_11_22_33_44_55_66/service000c/char000d"
        )
        == "/org/bluez/hci0/dev_11_22_33_44_55_66"
    )
