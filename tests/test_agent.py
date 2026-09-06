"""Tests for :mod:`bleak.agent`."""

import pytest

from bleak.agent import (
    ConfirmPasskey,
    DisplayPasskey,
    IOCapability,
    PairingCallbacks,
    RequestPasskey,
    io_capability,
)


async def _confirm(request: ConfirmPasskey) -> bool:
    return True


async def _request_passkey(request: RequestPasskey) -> int | None:
    return 0


async def _display_passkey(request: DisplayPasskey) -> None:
    return None


@pytest.mark.parametrize(
    ("callbacks", "expected"),
    [
        (PairingCallbacks(), IOCapability.NO_INPUT_NO_OUTPUT),
        (PairingCallbacks(confirm=_confirm), IOCapability.DISPLAY_YES_NO),
        (
            PairingCallbacks(request_passkey=_request_passkey),
            IOCapability.KEYBOARD_ONLY,
        ),
        (
            PairingCallbacks(display_passkey=_display_passkey),
            IOCapability.DISPLAY_ONLY,
        ),
        (
            PairingCallbacks(
                request_passkey=_request_passkey, display_passkey=_display_passkey
            ),
            IOCapability.KEYBOARD_DISPLAY,
        ),
        (
            PairingCallbacks(
                confirm=_confirm,
                request_passkey=_request_passkey,
                display_passkey=_display_passkey,
            ),
            IOCapability.KEYBOARD_DISPLAY,
        ),
    ],
)
def test_io_capability(callbacks: PairingCallbacks, expected: IOCapability) -> None:
    """The advertised capability is derived from which callbacks are provided."""
    assert io_capability(callbacks) == expected
