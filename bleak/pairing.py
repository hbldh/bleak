"""
Pairing
-------

Types for participating in the BLE pairing ceremony.

An application takes part in pairing by supplying an object that implements one or
more of the capability protocols in this module -- :class:`SupportsConfirm`,
:class:`SupportsRequestPasskey`, and :class:`SupportsDisplayPasskey`. Only the
methods for the ceremonies the application can perform are implemented; the
*absence* of a method means the application cannot take part in that ceremony.
Which methods are present determines the input/output capability that Bleak
advertises to the peer, and therefore which `Security Manager`_ pairing method is
negotiated:

============================================  =====================  =======================
Implemented methods                           Capability             Ceremony
============================================  =====================  =======================
(none)                                        ``NoInputNoOutput``    Just Works
``confirm``                                   ``DisplayYesNo``       Numeric Comparison
``request_passkey``                           ``KeyboardOnly``       Passkey Entry (input)
``display_passkey``                           ``DisplayOnly``        Passkey Entry (output)
``request_passkey`` + ``display_passkey``     ``KeyboardDisplay``    Passkey Entry (either)
============================================  =====================  =======================

A ``confirm`` method also implies a display, since Numeric Comparison shows the
value being compared, so combining it with another method upgrades the advertised
capability (e.g. ``confirm`` + ``display_passkey`` is ``DisplayYesNo``, while
``confirm`` + ``request_passkey`` is ``KeyboardDisplay``).

There are two equivalent ways to supply an implementation:

* any object -- a :class:`~typing.NamedTuple` is a natural fit -- that structurally
  implements the chosen methods, or
* a subclass of the matching protocols -- :class:`SupportsConfirm`,
  :class:`SupportsRequestPasskey`, :class:`SupportsDisplayPasskey`. Their methods are
  abstract, so the type checker *and* the interpreter require you to implement every
  capability you inherit (merely inheriting is not enough); state may be carried on
  ``self``, and the protocols may be combined freely by multiple inheritance.

Because detection is structural (see :func:`io_capability`), implement *only* the
methods for the ceremonies you support and omit the rest; a method that is present
but does not work (for example, one that always raises) still advertises the
capability, which is almost never what you want.

The IO capabilities and their mapping to a pairing method follow the `Security
Manager`_ specification: Bluetooth Core Specification v5.4, Vol 3, Part H, Section
2.3.2 (IO capabilities) and Section 2.3.5.1 (mapping of IO capabilities to the key
generation method).

.. _Security Manager: https://www.bluetooth.com/specifications/specs/core-specification/
"""

from abc import abstractmethod
from enum import Enum, auto
from typing import Final, Protocol, TypeAlias, runtime_checkable

from bleak.backends.device import BLEDevice

MAX_PASSKEY: Final = 999999
"""The largest valid BLE passkey; passkeys are six decimal digits (000000-999999)."""


@runtime_checkable
class SupportsConfirm(Protocol):
    """Capability to take part in Numeric Comparison (``DisplayYesNo``)."""

    @abstractmethod
    async def confirm(self, device: BLEDevice, passkey: int) -> bool:
        """Numeric Comparison: receive *device* and the *passkey* shown on both
        devices; return ``True`` to accept the pairing or ``False`` to reject it."""


@runtime_checkable
class SupportsRequestPasskey(Protocol):
    """Capability to enter a passkey for Passkey Entry (``KeyboardOnly``)."""

    @abstractmethod
    async def request_passkey(self, device: BLEDevice) -> int | None:
        """Passkey Entry (input): return the passkey the peer is displaying -- an
        integer from ``0`` to :data:`MAX_PASSKEY` -- or ``None`` to reject the
        pairing. ``0`` (``000000``) is itself a valid passkey, so rejection is
        signalled only by ``None``, never by a falsy return value."""


@runtime_checkable
class SupportsDisplayPasskey(Protocol):
    """Capability to display a passkey for Passkey Entry (``DisplayOnly``)."""

    @abstractmethod
    async def display_passkey(self, device: BLEDevice, passkey: int) -> None:
        """Passkey Entry (output): display the given *passkey* for the user to enter
        on the peer device."""


PairingCallbacks: TypeAlias = (
    SupportsConfirm | SupportsRequestPasskey | SupportsDisplayPasskey
)
"""An object implementing one or more pairing capabilities.

This is the type backends accept (as ``PairingCallbacks | None``, where ``None``
means no callbacks and selects Just Works). Satisfy it with any object -- a
:class:`~typing.NamedTuple` is a natural fit -- that defines the chosen methods, or
by subclassing :class:`SupportsConfirm`, :class:`SupportsRequestPasskey`, and/or
:class:`SupportsDisplayPasskey`.
"""


class IOCapability(Enum):
    """The input/output capability advertised to the peer during pairing.

    These are the five IO capabilities defined by the Bluetooth Core
    Specification (Vol 3, Part H, Section 2.3.2), named in Pythonic form (BlueZ,
    for example, spells them ``NoInputNoOutput``, ``DisplayYesNo``, and so on).
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


def io_capability(callbacks: PairingCallbacks | None) -> IOCapability:
    """Derive the advertised :class:`IOCapability` from *callbacks*.

    Detection is structural: each capability is present when *callbacks* implements
    the corresponding method. ``None`` (no callbacks) maps to ``NoInputNoOutput``,
    which selects the Just Works ceremony on backends that support pairing. A
    ``confirm`` method implies a display, since Numeric Comparison shows the value
    being confirmed.
    """
    can_input = isinstance(callbacks, SupportsRequestPasskey)
    can_confirm = isinstance(callbacks, SupportsConfirm)
    can_display = isinstance(callbacks, SupportsDisplayPasskey) or can_confirm
    if can_input and can_display:
        return IOCapability.KEYBOARD_DISPLAY
    if can_input:
        return IOCapability.KEYBOARD_ONLY
    if can_confirm:
        return IOCapability.DISPLAY_YES_NO
    if can_display:
        return IOCapability.DISPLAY_ONLY
    return IOCapability.NO_INPUT_NO_OUTPUT
