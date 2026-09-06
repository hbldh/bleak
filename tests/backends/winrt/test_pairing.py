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

from bleak.agent import ConfirmPasskey, DisplayPasskey, PairingCallbacks, RequestPasskey
from bleak.backends.winrt.client import (
    _pairing_kinds,  # pyright: ignore[reportPrivateUsage]
)
from bleak.backends.winrt.client import BleakClientWinRT


async def _confirm(request: ConfirmPasskey) -> bool:
    return True


async def _request_passkey(request: RequestPasskey) -> int | None:
    return 0


async def _display_passkey(request: DisplayPasskey) -> None:
    return None


@pytest.mark.parametrize(
    ("callbacks", "expected"),
    [
        (None, DevicePairingKinds.CONFIRM_ONLY),
        (PairingCallbacks(), DevicePairingKinds.CONFIRM_ONLY),
        (
            PairingCallbacks(confirm=_confirm),
            DevicePairingKinds.CONFIRM_ONLY | DevicePairingKinds.CONFIRM_PIN_MATCH,
        ),
        (
            PairingCallbacks(request_passkey=_request_passkey),
            DevicePairingKinds.CONFIRM_ONLY | DevicePairingKinds.PROVIDE_PIN,
        ),
        (
            PairingCallbacks(display_passkey=_display_passkey),
            DevicePairingKinds.CONFIRM_ONLY | DevicePairingKinds.DISPLAY_PIN,
        ),
        (
            PairingCallbacks(
                confirm=_confirm,
                request_passkey=_request_passkey,
                display_passkey=_display_passkey,
            ),
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
    """Each provided callback adds the pairing kind it can take part in."""
    assert _pairing_kinds(callbacks) == expected


def _make_client(monkeypatch: pytest.MonkeyPatch) -> BleakClientWinRT:
    client = BleakClientWinRT("AA:BB:CC:DD:EE:FF", winrt={}, timeout=10.0)
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

    async def confirm(request: ConfirmPasskey) -> bool:
        seen.append(request.passkey)
        return True

    args = _make_args(DevicePairingKinds.CONFIRM_PIN_MATCH, pin="123456")

    await _dispatch(client, args, PairingCallbacks(confirm=confirm))

    assert seen == [123456]
    args.accept.assert_called_once_with()


async def test_accept_numeric_comparison_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Numeric Comparison does not accept when the confirm callback returns False."""
    client = _make_client(monkeypatch)

    async def confirm(request: ConfirmPasskey) -> bool:
        return False

    args = _make_args(DevicePairingKinds.CONFIRM_PIN_MATCH)

    await _dispatch(client, args, PairingCallbacks(confirm=confirm))

    args.accept.assert_not_called()


async def test_accept_provide_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Passkey Entry accepts with the zero-padded passkey from the callback."""
    client = _make_client(monkeypatch)

    async def request_passkey(request: RequestPasskey) -> int | None:
        return 42

    args = _make_args(DevicePairingKinds.PROVIDE_PIN)

    await _dispatch(client, args, PairingCallbacks(request_passkey=request_passkey))

    args.accept_with_pin.assert_called_once_with("000042")


async def test_accept_provide_pin_none_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returning None from the passkey callback rejects the pairing."""
    client = _make_client(monkeypatch)

    async def request_passkey(request: RequestPasskey) -> int | None:
        return None

    args = _make_args(DevicePairingKinds.PROVIDE_PIN)

    await _dispatch(client, args, PairingCallbacks(request_passkey=request_passkey))

    args.accept_with_pin.assert_not_called()


async def test_accept_display_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Display Pin shows the passkey to the callback then accepts."""
    client = _make_client(monkeypatch)
    seen: list[int] = []

    async def display_passkey(request: DisplayPasskey) -> None:
        seen.append(request.passkey)

    args = _make_args(DevicePairingKinds.DISPLAY_PIN, pin="654321")

    await _dispatch(client, args, PairingCallbacks(display_passkey=display_passkey))

    assert seen == [654321]
    args.accept.assert_called_once_with()


async def test_accept_unsupported_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unsupported pairing kind is neither accepted nor crashes."""
    client = _make_client(monkeypatch)
    args = _make_args(DevicePairingKinds.PROVIDE_PASSWORD_CREDENTIAL)

    await _dispatch(client, args, None)

    args.accept.assert_not_called()
    args.accept_with_pin.assert_not_called()
