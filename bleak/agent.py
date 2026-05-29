"""
Pairing agent
-------------

Types for participating in the BLE pairing ceremony.

A :class:`PairingCallbacks` is a collection of optional asynchronous handlers,
one per ceremony that the application is able to take part in. Which handlers
are provided determines the input/output capability that Bleak advertises to
the peer, and therefore which `Security Manager`_ pairing method is negotiated:

============================================  =====================  =======================
Provided callbacks                            Capability             Ceremony
============================================  =====================  =======================
(none)                                        ``NoInputNoOutput``    Just Works
``confirm``                                   ``DisplayYesNo``       Numeric Comparison
``request_passkey``                           ``KeyboardOnly``       Passkey Entry (input)
``display_passkey``                           ``DisplayOnly``        Passkey Entry (output)
``request_passkey`` + ``display_passkey``     ``KeyboardDisplay``    Passkey Entry (either)
============================================  =====================  =======================

.. _Security Manager: https://www.bluetooth.com/specifications/specs/core-specification/
"""

from collections.abc import Awaitable, Callable
from enum import Enum, auto
from typing import Final, NamedTuple, TypeAlias

from bleak.backends.device import BLEDevice

MAX_PASSKEY: Final = 999999
"""The largest valid BLE passkey; passkeys are six decimal digits (000000-999999)."""


class ConfirmPasskey(NamedTuple):
    """Request to confirm that the passkey shown by both devices matches.

    Delivered to :attr:`PairingCallbacks.confirm` during the Numeric Comparison
    ceremony. The callback returns ``True`` to accept the pairing or ``False``
    to reject it.
    """

    device: BLEDevice
    passkey: int


class RequestPasskey(NamedTuple):
    """Request to enter the passkey displayed by the peer device.

    Delivered to :attr:`PairingCallbacks.request_passkey` during the Passkey
    Entry ceremony when the local device is the input. The callback returns the
    passkey as an integer in the range ``0``..``999999``, or ``None`` to reject
    the pairing.
    """

    device: BLEDevice


class DisplayPasskey(NamedTuple):
    """Request to display a passkey for the user to enter on the peer device.

    Delivered to :attr:`PairingCallbacks.display_passkey` during the Passkey
    Entry ceremony when the local device is the output. The peer completes the
    ceremony when the user enters this passkey there.
    """

    device: BLEDevice
    passkey: int


PairingRequest: TypeAlias = ConfirmPasskey | RequestPasskey | DisplayPasskey
"""A request the peer raises during pairing, handled by a :class:`PairingCallbacks`."""


ConfirmCallback: TypeAlias = Callable[[ConfirmPasskey], Awaitable[bool]]
RequestPasskeyCallback: TypeAlias = Callable[[RequestPasskey], Awaitable[int | None]]
DisplayPasskeyCallback: TypeAlias = Callable[[DisplayPasskey], Awaitable[None]]


class PairingCallbacks(NamedTuple):
    """Application-provided handlers for the BLE pairing ceremony.

    Each field is an asynchronous callback invoked when the peer initiates the
    corresponding ceremony. A field left as ``None`` means the application
    cannot take part in that ceremony; the set of provided callbacks determines
    the advertised :class:`IOCapability` (see :func:`io_capability`). With no
    callbacks the Just Works ceremony is used and accepted automatically.
    """

    confirm: ConfirmCallback | None = None
    request_passkey: RequestPasskeyCallback | None = None
    display_passkey: DisplayPasskeyCallback | None = None


class IOCapability(Enum):
    """The input/output capability advertised to the peer during pairing.

    These mirror the Bluetooth Security Manager IO capabilities and the names
    used by the BlueZ agent API.
    """

    NO_INPUT_NO_OUTPUT = auto()
    """No way to display a six-digit value and no way to enter one or answer yes/no."""

    DISPLAY_YES_NO = auto()
    """Can display a six-digit value and has two buttons the user can map to yes and no."""

    KEYBOARD_ONLY = auto()
    """Can enter the digits 0-9 and answer yes/no, but cannot display a value."""

    DISPLAY_ONLY = auto()
    """Can display a six-digit value but has no input to enter one or answer yes/no."""

    KEYBOARD_DISPLAY = auto()
    """Can both display a six-digit value and enter one; LE only."""


def io_capability(callbacks: PairingCallbacks) -> IOCapability:
    """Derive the advertised :class:`IOCapability` from the provided callbacks."""
    can_input = callbacks.request_passkey is not None
    can_display = callbacks.display_passkey is not None
    if can_input and can_display:
        return IOCapability.KEYBOARD_DISPLAY
    if can_input:
        return IOCapability.KEYBOARD_ONLY
    if can_display:
        return IOCapability.DISPLAY_ONLY
    if callbacks.confirm is not None:
        return IOCapability.DISPLAY_YES_NO
    return IOCapability.NO_INPUT_NO_OUTPUT
