import sys

import pytest


def pytest_addoption(
    parser: pytest.Parser,
) -> None:
    parser.addoption(
        "--bleak-hci-transport",
        action="store",
        default=None,
        help="Bumble HCI transport moniker",
    )

    parser.addoption(
        "--bleak-bluez-vhci",
        action="store_true",
        default=False,
        help="Enable BlueZ VHCI Bumble HCI transport",
    )


def pytest_report_header(config: pytest.Config) -> str:
    from bleak.backends import BleakBackend, get_default_backend

    default_backend = get_default_backend()

    header = f"bleak backend: {default_backend.value}"
    if sys.platform == "darwin" and default_backend == BleakBackend.CORE_BLUETOOTH:
        from bleak.backends.corebluetooth._objc_compat import get_objc_framework

        header += f" ({get_objc_framework().value})"
    return header
