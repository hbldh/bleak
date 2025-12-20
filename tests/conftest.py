import pytest


def pytest_addoption(
    parser: pytest.Parser,
) -> None:
    parser.addoption(
        "--bleak-hci-transport",
        action="store",
        default=None,
        help="Bumble HCI transport monkier",
    )

    parser.addoption(
        "--bleak-bluez-hci-transport",
        action="store",
        default=None,
        help="Bumble HCI transport monkier to BlueZ",
    )
