"""Tests for the :class:`~bleak.BleakClient` ``pairing_callbacks`` argument."""

from typing import Any
from unittest.mock import MagicMock

from bleak import BleakClient
from bleak.backends.device import BLEDevice

ADDRESS = "AA:BB:CC:DD:EE:FF"


class _Confirmer:
    """A minimal object satisfying :class:`~bleak.pairing.SupportsConfirm`."""

    async def confirm(self, device: BLEDevice, passkey: int) -> bool:
        return True


def _fake_backend() -> MagicMock:
    backend = MagicMock()
    backend.__name__ = "FakeBackend"
    return backend


def _client(backend: MagicMock, **kwargs: Any) -> None:
    """Construct a ``BleakClient`` whose backend class is the given mock."""
    BleakClient(ADDRESS, backend=backend, **kwargs)  # type: ignore[arg-type]


def test_pairing_callbacks_forwarded_to_backend() -> None:
    backend = _fake_backend()
    callbacks = _Confirmer()
    _client(backend, pairing_callbacks=callbacks, pair=True)
    assert backend.call_args.kwargs["pairing_callbacks"] is callbacks


def test_default_pairing_callbacks_forwarded_to_backend() -> None:
    backend = _fake_backend()
    _client(backend)
    assert backend.call_args.kwargs["pairing_callbacks"] is None
