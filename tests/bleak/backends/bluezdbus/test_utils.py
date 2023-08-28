#!/usr/bin/env python

"""Tests for `bleak.backends.bluezdbus.utils` package."""

import pytest
import sys


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="requires dbus-fast on Linux"
)
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
