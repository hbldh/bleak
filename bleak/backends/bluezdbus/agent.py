"""
Agent
-----

Implements the BlueZ ``org.bluez.Agent1`` D-Bus interface and binds it to a
:class:`~bleak.pairing.PairingCallbacks`. See the BlueZ `agent API
<https://github.com/bluez/bluez/blob/master/doc/org.bluez.Agent.rst>`_.

The D-Bus method signatures use the typed aliases from
:mod:`dbus_fast.annotations` so that the wire signatures are carried as real
types and static type checkers can verify the method bodies.
"""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Awaitable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, TypeVar

from dbus_fast import DBusError, Message
from dbus_fast.aio import MessageBus
from dbus_fast.annotations import DBusObjectPath, DBusStr, DBusUInt16, DBusUInt32
from dbus_fast.service import ServiceInterface
from dbus_fast.service import method as dbus_method

from bleak._compat import assert_never
from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.manager import get_global_bluez_manager
from bleak.backends.bluezdbus.utils import assert_reply
from bleak.backends.device import BLEDevice
from bleak.pairing import (
    MAX_PASSKEY,
    IOCapability,
    PairingCallbacks,
    SupportsConfirm,
    SupportsDisplayPasskey,
    SupportsRequestPasskey,
    io_capability,
)

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def capability_name(capability: IOCapability) -> str:
    """Map an :class:`IOCapability` to the BlueZ agent capability string."""
    match capability:
        case IOCapability.NO_INPUT_NO_OUTPUT:
            return "NoInputNoOutput"
        case IOCapability.DISPLAY_YES_NO:
            return "DisplayYesNo"
        case IOCapability.KEYBOARD_ONLY:
            return "KeyboardOnly"
        case IOCapability.DISPLAY_ONLY:
            return "DisplayOnly"
        case IOCapability.KEYBOARD_DISPLAY:
            return "KeyboardDisplay"
        case _:
            assert_never(capability)


class Agent(ServiceInterface):
    """The ``org.bluez.Agent1`` interface backed by a :class:`PairingCallbacks`."""

    def __init__(self, callbacks: PairingCallbacks | None) -> None:
        super().__init__(defs.AGENT_INTERFACE)
        self._callbacks = callbacks
        self._pending: asyncio.Future[Any] | None = None

    @staticmethod
    async def _ble_device(device_path: str) -> BLEDevice:
        manager = await get_global_bluez_manager()
        return BLEDevice(
            manager.get_device_address(device_path),
            manager.get_device_name(device_path),
            {"path": device_path},
        )

    async def _run(self, awaitable: Awaitable[_T]) -> _T:
        """Await an *awaitable*, mapping cancellation to a D-Bus error.

        The awaitable is held so a concurrent :meth:`Cancel` can abort the in-flight
        future without disturbing dbus-fast's own dispatch task.
        """
        self._pending = asyncio.ensure_future(awaitable)
        try:
            return await self._pending
        except asyncio.CancelledError:
            raise DBusError("org.bluez.Error.Canceled", "pairing canceled")
        finally:
            self._pending = None

    async def _confirm(self, device_path: str, passkey: int) -> None:
        callbacks = self._callbacks
        if not isinstance(callbacks, SupportsConfirm):
            raise DBusError(
                "org.bluez.Error.Rejected", "numeric comparison not supported"
            )
        device = await self._ble_device(device_path)
        if not await self._run(callbacks.confirm(device, passkey)):
            raise DBusError("org.bluez.Error.Rejected", "pairing rejected")

    async def _request_passkey(self, device_path: str) -> int:
        callbacks = self._callbacks
        if not isinstance(callbacks, SupportsRequestPasskey):
            raise DBusError("org.bluez.Error.Rejected", "passkey entry not supported")
        device = await self._ble_device(device_path)
        passkey = await self._run(callbacks.request_passkey(device))
        if passkey is None:
            raise DBusError("org.bluez.Error.Rejected", "pairing rejected")
        if not 0 <= passkey <= MAX_PASSKEY:
            raise DBusError(
                "org.bluez.Error.Rejected", f"passkey {passkey} out of range"
            )
        return passkey

    async def _display(self, device_path: str, passkey: int) -> None:
        callbacks = self._callbacks
        if not isinstance(callbacks, SupportsDisplayPasskey):
            logger.debug("no display_passkey support; ignoring DisplayPasskey")
            return
        device = await self._ble_device(device_path)
        await self._run(callbacks.display_passkey(device, passkey))

    @dbus_method()
    def Release(self) -> None:
        logger.debug("pairing agent released")

    @dbus_method()
    async def RequestPinCode(self, device: DBusObjectPath) -> DBusStr:
        raise DBusError(
            "org.bluez.Error.Rejected", "legacy PIN code pairing not supported"
        )

    @dbus_method()
    async def DisplayPinCode(self, device: DBusObjectPath, pincode: DBusStr) -> None:
        raise DBusError(
            "org.bluez.Error.Rejected", "legacy PIN code pairing not supported"
        )

    @dbus_method()
    async def RequestPasskey(self, device: DBusObjectPath) -> DBusUInt32:
        return await self._request_passkey(device)

    @dbus_method()
    async def DisplayPasskey(
        self, device: DBusObjectPath, passkey: DBusUInt32, entered: DBusUInt16
    ) -> None:
        await self._display(device, passkey)

    @dbus_method()
    async def RequestConfirmation(
        self, device: DBusObjectPath, passkey: DBusUInt32
    ) -> None:
        await self._confirm(device, passkey)

    @dbus_method()
    async def RequestAuthorization(self, device: DBusObjectPath) -> None:
        logger.debug("authorizing just works pairing for %s", device)

    @dbus_method()
    async def AuthorizeService(self, device: DBusObjectPath, uuid: DBusStr) -> None:
        raise DBusError(
            "org.bluez.Error.Rejected", "service authorization not supported"
        )

    @dbus_method()
    def Cancel(self) -> None:
        logger.debug("pairing canceled by peer")
        if self._pending is not None:
            self._pending.cancel()


async def _register_agent(bus: MessageBus, agent_path: str, capability: str) -> None:
    reply = await bus.call(
        Message(
            destination=defs.BLUEZ_SERVICE,
            path="/org/bluez",
            interface=defs.AGENT_MANAGER_INTERFACE,
            member="RegisterAgent",
            signature="os",
            body=[agent_path, capability],
        )
    )
    assert reply is not None
    assert_reply(reply)


async def _unregister_agent(bus: MessageBus, agent_path: str) -> None:
    reply = await bus.call(
        Message(
            destination=defs.BLUEZ_SERVICE,
            path="/org/bluez",
            interface=defs.AGENT_MANAGER_INTERFACE,
            member="UnregisterAgent",
            signature="o",
            body=[agent_path],
        )
    )
    assert reply is not None
    assert_reply(reply)


@asynccontextmanager
async def bluez_agent(
    bus: MessageBus, callbacks: PairingCallbacks | None = None
) -> AsyncGenerator[None]:
    """Register a pairing :class:`Agent` for the duration of the context.

    The advertised capability is derived from *callbacks* via
    :func:`~bleak.pairing.io_capability`. With the default (empty)
    :class:`~bleak.pairing.PairingCallbacks`, a Just Works agent is registered.
    A unique object path keeps multiple Bleak agents (and interpreters) from
    colliding.
    """
    agent = Agent(callbacks)
    agent_path = f"/org/bleak/agent/{os.getpid()}/{id(agent)}"
    capability = capability_name(io_capability(callbacks))

    async with AsyncExitStack() as stack:
        bus.export(agent_path, agent)
        stack.callback(bus.unexport, agent_path, agent)
        await _register_agent(bus, agent_path, capability)
        stack.push_async_callback(_unregister_agent, bus, agent_path)
        yield
