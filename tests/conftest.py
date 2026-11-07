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
        "--bleak-vhci",
        action="store_true",
        default=False,
        help="Enable the OS's virtual HCI transport: the vhci driver with BlueZ "
        "on Linux, the winvhci driver on Windows",
    )

    parser.addoption(
        "--bleak-bluez-vhci",
        action="store_true",
        default=False,
        help="Deprecated alias for --bleak-vhci",
    )
