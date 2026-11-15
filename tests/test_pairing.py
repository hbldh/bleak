"""Tests for :mod:`bleak.pairing`.

Coverage is split across the ways an application may supply pairing callbacks --
subclassing the capability protocols and defining a plain (structurally typed)
object such as a :class:`~typing.NamedTuple` -- and across both the runtime
behaviour of :func:`~bleak.pairing.io_capability` and the static typing of the
protocols.
"""

from typing import NamedTuple, TypeAlias

import pytest

from bleak._compat import assert_never, assert_type
from bleak.backends.device import BLEDevice
from bleak.pairing import (
    IOCapability,
    PairingCallbacks,
    SupportsConfirm,
    SupportsDisplayPasskey,
    SupportsRequestPasskey,
    io_capability,
)

DEVICE = BLEDevice("AA:BB:CC:DD:EE:FF", None, None)


class _Confirm(SupportsConfirm):
    async def confirm(self, device: BLEDevice, passkey: int) -> bool:
        return True


class _Request(SupportsRequestPasskey):
    async def request_passkey(self, device: BLEDevice) -> int | None:
        return 0


class _Display(SupportsDisplayPasskey):
    async def display_passkey(self, device: BLEDevice, passkey: int) -> None:
        return None


class _ConfirmRequest(_Confirm, _Request):
    pass


class _ConfirmDisplay(_Confirm, _Display):
    pass


class _RequestDisplay(_Request, _Display):
    pass


class _All(_Confirm, _Request, _Display):
    pass


class TupleConfirm(NamedTuple):
    async def confirm(self, device: BLEDevice, passkey: int) -> bool:
        return True


class TupleRequestDisplay(NamedTuple):
    passkey: int

    async def request_passkey(self, device: BLEDevice) -> int | None:
        return self.passkey

    async def display_passkey(self, device: BLEDevice, passkey: int) -> None:
        return None


class _DuckConfirm:
    async def confirm(self, device: BLEDevice, passkey: int) -> bool:
        return True


class _DuckRequest:
    async def request_passkey(self, device: BLEDevice) -> int | None:
        return 0


class _DuckDisplay:
    async def display_passkey(self, device: BLEDevice, passkey: int) -> None:
        return None


class _DuckConfirmRequest(_DuckConfirm, _DuckRequest):
    pass


class _DuckConfirmDisplay(_DuckConfirm, _DuckDisplay):
    pass


class _DuckRequestDisplay(_DuckRequest, _DuckDisplay):
    pass


class _DuckAll(_DuckConfirm, _DuckRequest, _DuckDisplay):
    pass


@pytest.mark.parametrize(
    ("callbacks", "expected"),
    [
        (None, IOCapability.NO_INPUT_NO_OUTPUT),
        (_Confirm(), IOCapability.DISPLAY_YES_NO),
        (_Request(), IOCapability.KEYBOARD_ONLY),
        (_Display(), IOCapability.DISPLAY_ONLY),
        (_ConfirmRequest(), IOCapability.KEYBOARD_DISPLAY),
        (_ConfirmDisplay(), IOCapability.DISPLAY_YES_NO),
        (_RequestDisplay(), IOCapability.KEYBOARD_DISPLAY),
        (_All(), IOCapability.KEYBOARD_DISPLAY),
    ],
)
def test_io_capability(
    callbacks: PairingCallbacks | None, expected: IOCapability
) -> None:
    """Every combination of implemented methods maps to the documented capability."""
    assert io_capability(callbacks) is expected


@pytest.mark.parametrize(
    ("callbacks", "expected"),
    [
        (TupleConfirm(), IOCapability.DISPLAY_YES_NO),
        (TupleRequestDisplay(passkey=0), IOCapability.KEYBOARD_DISPLAY),
    ],
)
def test_io_capability_namedtuple(
    callbacks: PairingCallbacks, expected: IOCapability
) -> None:
    """A user-supplied NamedTuple is detected the same way as a protocol subclass."""
    assert io_capability(callbacks) is expected


@pytest.mark.parametrize(
    ("callbacks", "expected"),
    [
        (_DuckConfirm(), IOCapability.DISPLAY_YES_NO),
        (_DuckRequest(), IOCapability.KEYBOARD_ONLY),
        (_DuckDisplay(), IOCapability.DISPLAY_ONLY),
        (_DuckConfirmRequest(), IOCapability.KEYBOARD_DISPLAY),
        (_DuckConfirmDisplay(), IOCapability.DISPLAY_YES_NO),
        (_DuckRequestDisplay(), IOCapability.KEYBOARD_DISPLAY),
        (_DuckAll(), IOCapability.KEYBOARD_DISPLAY),
    ],
)
def test_io_capability_structural(
    callbacks: PairingCallbacks, expected: IOCapability
) -> None:
    """A plain object that matches the protocols only structurally (it does not
    subclass them) is detected across every non-empty combination -- a protocol
    subclass can satisfy isinstance nominally and skip this purely structural path."""
    assert io_capability(callbacks) is expected


def test_isinstance_reflects_implemented_methods() -> None:
    """The runtime-checkable protocols match on the presence of their method."""
    assert isinstance(_Confirm(), SupportsConfirm)
    assert not isinstance(_Confirm(), SupportsRequestPasskey)
    assert not isinstance(_Confirm(), SupportsDisplayPasskey)

    assert isinstance(_RequestDisplay(), SupportsRequestPasskey)
    assert isinstance(_RequestDisplay(), SupportsDisplayPasskey)
    assert not isinstance(_RequestDisplay(), SupportsConfirm)


def test_present_but_broken_method_still_advertises() -> None:
    """The runtime-checkable protocols match on method *presence*, not on whether
    the method actually works -- so a present-but-broken handler still advertises
    the capability. This is why io_capability cannot validate behaviour and the
    docs tell implementers to omit unsupported ceremonies rather than stub them."""

    class BrokenConfirm:
        async def confirm(self, device: BLEDevice, passkey: int) -> bool:
            raise RuntimeError("confirm is not really implemented")

    agent = BrokenConfirm()
    assert isinstance(agent, SupportsConfirm)
    assert io_capability(agent) is IOCapability.DISPLAY_YES_NO


class _IncompleteConfirm(SupportsConfirm):
    pass


class _IncompleteRequest(SupportsRequestPasskey):
    pass


class _IncompleteDisplay(SupportsDisplayPasskey):
    pass


_IncompleteSubclass: TypeAlias = (
    type[_IncompleteConfirm] | type[_IncompleteRequest] | type[_IncompleteDisplay]
)


@pytest.mark.parametrize(
    "incomplete", [_IncompleteConfirm, _IncompleteRequest, _IncompleteDisplay]
)
def test_protocol_subclass_without_override_cannot_instantiate(
    incomplete: _IncompleteSubclass,
) -> None:
    """Inheriting a capability protocol but not implementing its method is an error
    at instantiation -- the protocol methods are abstract -- so a user who merely
    inherits cannot end up with a silently broken handler."""
    with pytest.raises(TypeError):
        incomplete()  # type: ignore[abstract]


async def test_callbacks_are_invocable() -> None:
    """The implemented methods are awaitable with the documented signatures."""
    agent = _All()
    assert await agent.confirm(DEVICE, 123456) is True
    assert await agent.request_passkey(DEVICE) == 0
    await agent.display_passkey(DEVICE, 123456)


async def test_namedtuple_implementation_with_state() -> None:
    """A user can implement the callbacks as a NamedTuple that carries state: it is
    detected by :func:`io_capability`, and its method behaves per that state."""

    class MyPairing(NamedTuple):
        accepted_passkey: int

        async def confirm(self, device: BLEDevice, passkey: int) -> bool:
            return passkey == self.accepted_passkey

    callbacks = MyPairing(accepted_passkey=123456)
    assert io_capability(callbacks) is IOCapability.DISPLAY_YES_NO
    assert await callbacks.confirm(DEVICE, 123456) is True
    assert await callbacks.confirm(DEVICE, 999999) is False


def _opaque() -> object:
    """Return a value statically typed as ``object`` so the ``isinstance`` narrowing
    in :func:`test_static_typing` is a real check rather than a tautology on an
    already-known type."""
    return _Confirm()


def test_static_typing() -> None:
    """Static guarantees: the return type, and protocol narrowing via isinstance."""
    assert_type(io_capability(None), IOCapability)

    candidate = _opaque()
    if isinstance(candidate, SupportsConfirm):
        assert_type(candidate, SupportsConfirm)


def test_static_assignability() -> None:
    """Both supply mechanisms satisfy ``PairingCallbacks`` statically: every element
    of this list is type-checked against the annotation."""
    accepted: list[PairingCallbacks | None] = [
        None,
        _All(),
        TupleConfirm(),
        TupleRequestDisplay(passkey=0),
    ]
    assert len(accepted) == 4


def _capability_name(capability: IOCapability) -> str:
    match capability:
        case IOCapability.NO_INPUT_NO_OUTPUT:
            return "NoInputNoOutput"
        case IOCapability.DISPLAY_ONLY:
            return "DisplayOnly"
        case IOCapability.DISPLAY_YES_NO:
            return "DisplayYesNo"
        case IOCapability.KEYBOARD_ONLY:
            return "KeyboardOnly"
        case IOCapability.KEYBOARD_DISPLAY:
            return "KeyboardDisplay"
        case _ as unreachable:
            assert_never(unreachable)


def test_capability_name() -> None:
    """Each member maps to its specific name. (``assert_never`` in
    :func:`_capability_name` separately proves *static* exhaustiveness, so adding a
    member without a case is a type error.)"""
    assert _capability_name(IOCapability.NO_INPUT_NO_OUTPUT) == "NoInputNoOutput"
    assert _capability_name(IOCapability.DISPLAY_ONLY) == "DisplayOnly"
    assert _capability_name(IOCapability.DISPLAY_YES_NO) == "DisplayYesNo"
    assert _capability_name(IOCapability.KEYBOARD_ONLY) == "KeyboardOnly"
    assert _capability_name(IOCapability.KEYBOARD_DISPLAY) == "KeyboardDisplay"
