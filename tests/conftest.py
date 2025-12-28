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
