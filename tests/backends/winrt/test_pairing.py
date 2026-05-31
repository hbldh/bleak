"""Tests for WinRT pairing-kind derivation and pairing-request dispatch."""

import sys
from typing import cast
from unittest.mock import MagicMock

import pytest

if sys.platform != "win32":
    pytest.skip("skipping windows-only tests", allow_module_level=True)
    assert False  # HACK: work around pyright bug

from winrt.windows.devices.enumeration import (
    DevicePairingKinds,
    DevicePairingRequestedEventArgs,
)

from bleak.backends.device import BLEDevice
from bleak.backends.winrt.client import (
    _pairing_kinds,  # pyright: ignore[reportPrivateUsage]
)
from bleak.backends.winrt.client import BleakClientWinRT
from bleak.pairing import (
    PairingCallbacks,
    SupportsConfirm,
    SupportsDisplayPasskey,
    SupportsRequestPasskey,
)


class _Confirm(SupportsConfirm):
    async def confirm(self, device: BLEDevice, passkey: int) -> bool:
        return True


class _Request(SupportsRequestPasskey):
    async def request_passkey(self, device: BLEDevice) -> int | None:
        return 0


class _Display(SupportsDisplayPasskey):
    async def display_passkey(self, device: BLEDevice, passkey: int) -> None:
        return None


class _All(_Confirm, _Request, _Display):
    pass


@pytest.mark.parametrize(
    ("callbacks", "expected"),
    [
        (None, DevicePairingKinds.CONFIRM_ONLY),
        (
            _Confirm(),
            DevicePairingKinds.CONFIRM_ONLY | DevicePairingKinds.CONFIRM_PIN_MATCH,
        ),
        (
            _Request(),
            DevicePairingKinds.CONFIRM_ONLY | DevicePairingKinds.PROVIDE_PIN,
        ),
        (
            _Display(),
            DevicePairingKinds.CONFIRM_ONLY | DevicePairingKinds.DISPLAY_PIN,
        ),
        (
            _All(),
            DevicePairingKinds.CONFIRM_ONLY
            | DevicePairingKinds.CONFIRM_PIN_MATCH
            | DevicePairingKinds.PROVIDE_PIN
            | DevicePairingKinds.DISPLAY_PIN,
        ),
    ],
)
def test_pairing_kinds(
    callbacks: PairingCallbacks | None, expected: DevicePairingKinds
) -> None:
    """Each provided capability adds the pairing kind it can take part in."""
    assert _pairing_kinds(callbacks) == expected


def _make_client(monkeypatch: pytest.MonkeyPatch) -> BleakClientWinRT:
    client = BleakClientWinRT(
        "AA:BB:CC:DD:EE:FF", winrt={}, timeout=10.0, disconnected_callback=None
    )
    requester = MagicMock()
    requester.name = "Test Device"
    monkeypatch.setattr(client, "_requester", requester)
    return client


def _make_args(kind: DevicePairingKinds, pin: str = "123456") -> MagicMock:
    args = MagicMock(spec=DevicePairingRequestedEventArgs)
    args.pairing_kind = kind
    args.pin = pin
    return args


async def _dispatch(
    client: BleakClientWinRT, args: MagicMock, callbacks: PairingCallbacks | None
) -> None:
    await client._accept_pairing(  # pyright: ignore[reportPrivateUsage]
        cast(DevicePairingRequestedEventArgs, args), callbacks
    )


async def test_accept_confirm_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Just Works is accepted without any callback."""
    client = _make_client(monkeypatch)
    args = _make_args(DevicePairingKinds.CONFIRM_ONLY)

    await _dispatch(client, args, None)

    args.accept.assert_called_once_with()


async def test_accept_numeric_comparison_confirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Numeric Comparison accepts when the confirm callback returns True."""
    client = _make_client(monkeypatch)
    seen: list[int] = []

    class _Confirmer(SupportsConfirm):
        async def confirm(self, device: BLEDevice, passkey: int) -> bool:
            seen.append(passkey)
            return True

    args = _make_args(DevicePairingKinds.CONFIRM_PIN_MATCH, pin="123456")

    await _dispatch(client, args, _Confirmer())

    assert seen == [123456]
    args.accept.assert_called_once_with()


async def test_accept_numeric_comparison_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Numeric Comparison does not accept when the confirm callback returns False."""
    client = _make_client(monkeypatch)

    class _Confirmer(SupportsConfirm):
        async def confirm(self, device: BLEDevice, passkey: int) -> bool:
            return False

    args = _make_args(DevicePairingKinds.CONFIRM_PIN_MATCH)

    await _dispatch(client, args, _Confirmer())

    args.accept.assert_not_called()


async def test_accept_provide_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Passkey Entry accepts with the zero-padded passkey from the callback."""
    client = _make_client(monkeypatch)

    class _Requester(SupportsRequestPasskey):
        async def request_passkey(self, device: BLEDevice) -> int | None:
            return 42

    args = _make_args(DevicePairingKinds.PROVIDE_PIN)

    await _dispatch(client, args, _Requester())

    args.accept_with_pin.assert_called_once_with("000042")


async def test_accept_provide_pin_none_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returning None from the passkey callback rejects the pairing."""
    client = _make_client(monkeypatch)

    class _Requester(SupportsRequestPasskey):
        async def request_passkey(self, device: BLEDevice) -> int | None:
            return None

    args = _make_args(DevicePairingKinds.PROVIDE_PIN)

    await _dispatch(client, args, _Requester())

    args.accept_with_pin.assert_not_called()


async def test_accept_display_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Display Pin shows the passkey to the callback then accepts."""
    client = _make_client(monkeypatch)
    seen: list[int] = []

    class _Displayer(SupportsDisplayPasskey):
        async def display_passkey(self, device: BLEDevice, passkey: int) -> None:
            seen.append(passkey)

    args = _make_args(DevicePairingKinds.DISPLAY_PIN, pin="654321")

    await _dispatch(client, args, _Displayer())

    assert seen == [654321]
    args.accept.assert_called_once_with()


async def test_accept_unsupported_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unsupported pairing kind is neither accepted nor crashes."""
    client = _make_client(monkeypatch)
    args = _make_args(DevicePairingKinds.PROVIDE_PASSWORD_CREDENTIAL)

    await _dispatch(client, args, None)

    args.accept.assert_not_called()
    args.accept_with_pin.assert_not_called()
