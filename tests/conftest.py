import pytest


def pytest_addoption(
    parser: pytest.Parser,
) -> None:
    parser.addoption(
        "--hci-transport",
        action="store",
        default=None,
        help="Bumble hci transport name",
    )
