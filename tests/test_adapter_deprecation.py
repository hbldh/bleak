from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

import pytest

from bleak import BleakClient, BleakScanner


@pytest.fixture(params=["scanner", "client"])
def backend_bluez_args(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Callable[..., dict[str, Any]]:
    backend = Mock()
    monkeypatch.setattr(
        f"bleak.get_platform_{request.param}_backend_type",
        lambda: (backend, "test"),
    )

    def create(**kwargs: Any) -> dict[str, Any]:
        if request.param == "scanner":
            BleakScanner(**kwargs)
        else:
            BleakClient("00:11:22:33:44:55", **kwargs)
        return backend.call_args.kwargs["bluez"]

    return create


def test_adapter_kwarg_does_not_change_defaults(
    backend_bluez_args: Callable[..., dict[str, Any]],
):
    with pytest.deprecated_call(match="the 'adapter' keyword argument is deprecated"):
        first = backend_bluez_args(adapter="hci1")
    with pytest.deprecated_call(match="the 'adapter' keyword argument is deprecated"):
        second = backend_bluez_args(adapter="hci2")

    assert first == {"adapter": "hci1"}
    assert second == {"adapter": "hci2"}
    assert backend_bluez_args() == {}


def test_adapter_kwarg_does_not_change_caller_bluez_args(
    backend_bluez_args: Callable[..., dict[str, Any]],
):
    bluez: dict[str, str] = {}
    with pytest.deprecated_call(match="the 'adapter' keyword argument is deprecated"):
        actual = backend_bluez_args(adapter="hci1", bluez=bluez)

    assert actual == {"adapter": "hci1"}
    assert bluez == {}


def test_explicit_bluez_adapter_takes_precedence(
    backend_bluez_args: Callable[..., dict[str, Any]],
):
    bluez = {"adapter": "hci2"}
    with pytest.deprecated_call(match="the 'adapter' keyword argument is deprecated"):
        actual = backend_bluez_args(adapter="hci1", bluez=bluez)

    assert actual == {"adapter": "hci2"}
    assert bluez == {"adapter": "hci2"}


async def test_adapter_kwarg_deprecated_in_scanner():
    with pytest.deprecated_call(
        match="the 'adapter' keyword argument is deprecated, use the 'bluez' kwarg instead"
    ):
        BleakScanner(adapter="hci0")


async def test_adapter_kwarg_deprecated_in_client():
    with pytest.deprecated_call(
        match="the 'adapter' keyword argument is deprecated, use the 'bluez' kwarg instead"
    ):
        BleakClient("00:11:22:33:44:55", adapter="hci0")
