"""
Agent
-----

Implements the BlueZ ``org.bluez.Agent1`` D-Bus interface and binds it to a
:class:`~bleak.agent.PairingCallbacks`. See the BlueZ `agent API
<https://github.com/bluez/bluez/blob/master/doc/agent-api.txt>`_.

The D-Bus methods carry their wire signatures as string annotations (``"o"``,
``"u"``, ...) which dbus-fast parses but static type checkers cannot, so each
such method is a thin ``@no_type_check`` shim delegating to a fully typed
helper.
"""

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    if sys.platform != "linux":
        assert False, "This backend is only available on Linux"

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import TypeAlias, no_type_check

from dbus_fast import DBusError, Message
from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface
from dbus_fast.service import method as dbus_method

from bleak._compat import assert_never
from bleak.agent import (
    MAX_PASSKEY,
    ConfirmPasskey,
    DisplayPasskey,
    IOCapability,
    PairingCallbacks,
    RequestPasskey,
    io_capability,
)
from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.manager import get_global_bluez_manager
from bleak.backends.bluezdbus.utils import assert_reply
from bleak.backends.device import BLEDevice

logger = logging.getLogger(__name__)

_PendingTask: TypeAlias = asyncio.Task[bool] | asyncio.Task[int | None]


def _capability_name(capability: IOCapability) -> str:
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

    def __init__(self, callbacks: PairingCallbacks) -> None:
        super().__init__(defs.AGENT_INTERFACE)
        self._callbacks = callbacks
        self._pending: _PendingTask | None = None

    @staticmethod
    async def _ble_device(device_path: str) -> BLEDevice:
        manager = await get_global_bluez_manager()
        return BLEDevice(
            manager.get_device_address(device_path),
            manager.get_device_name(device_path),
            {"path": device_path},
        )

    async def _run(self, task: _PendingTask) -> bool | int | None:
        """Await a callback *task*, mapping cancellation to a D-Bus error.

        The task is held so a concurrent :meth:`Cancel` can abort the in-flight
        callback without disturbing dbus-fast's own dispatch task.
        """
        self._pending = task
        try:
            return await task
        except asyncio.CancelledError:
            raise DBusError("org.bluez.Error.Canceled", "pairing canceled")
        finally:
            self._pending = None

    async def _confirm(self, device_path: str, passkey: int) -> None:
        if (confirm := self._callbacks.confirm) is None:
            raise DBusError(
                "org.bluez.Error.Rejected", "numeric comparison not supported"
            )
        device = await self._ble_device(device_path)
        if not await self._run(
            asyncio.ensure_future(confirm(ConfirmPasskey(device, passkey)))
        ):
            raise DBusError("org.bluez.Error.Rejected", "pairing rejected")

    async def _request_passkey(self, device_path: str) -> int:
        if (request := self._callbacks.request_passkey) is None:
            raise DBusError("org.bluez.Error.Rejected", "passkey entry not supported")
        device = await self._ble_device(device_path)
        passkey = await self._run(
            asyncio.ensure_future(request(RequestPasskey(device)))
        )
        if passkey is None:
            raise DBusError("org.bluez.Error.Rejected", "pairing rejected")
        if not 0 <= passkey <= MAX_PASSKEY:
            raise DBusError(
                "org.bluez.Error.Rejected", f"passkey {passkey} out of range"
            )
        return passkey

    async def _display(self, device_path: str, passkey: int) -> None:
        if (display := self._callbacks.display_passkey) is None:
            return
        device = await self._ble_device(device_path)
        await display(DisplayPasskey(device, passkey))

    @dbus_method()
    def Release(self) -> None:  # noqa: N802
        logger.debug("pairing agent released")

    @dbus_method()
    @no_type_check
    async def RequestPinCode(self, device: "o") -> "s":  # noqa: F821 N802
        raise DBusError(
            "org.bluez.Error.Rejected", "legacy PIN code pairing not supported"
        )

    @dbus_method()
    @no_type_check
    async def DisplayPinCode(self, device: "o", pincode: "s"):  # noqa: F821 N802
        raise DBusError(
            "org.bluez.Error.Rejected", "legacy PIN code pairing not supported"
        )

    @dbus_method()
    @no_type_check
    async def RequestPasskey(self, device: "o") -> "u":  # noqa: F821 N802
        return await self._request_passkey(device)

    @dbus_method()
    @no_type_check
    async def DisplayPasskey(
        self, device: "o", passkey: "u", entered: "q"  # noqa: F821
    ):  # noqa: N802
        await self._display(device, passkey)

    @dbus_method()
    @no_type_check
    async def RequestConfirmation(self, device: "o", passkey: "u"):  # noqa: F821 N802
        await self._confirm(device, passkey)

    @dbus_method()
    @no_type_check
    async def RequestAuthorization(self, device: "o"):  # noqa: F821 N802
        logger.debug("authorizing just works pairing for %s", device)

    @dbus_method()
    @no_type_check
    async def AuthorizeService(self, device: "o", uuid: "s"):  # noqa: F821 N802
        raise DBusError(
            "org.bluez.Error.Rejected", "service authorization not supported"
        )

    @dbus_method()
    def Cancel(self) -> None:  # noqa: N802
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
    :func:`~bleak.agent.io_capability`. Omitting *callbacks* (or passing
    ``None``) registers a Just Works agent. A unique object path keeps multiple
    Bleak agents (and interpreters) from colliding.
    """
    callbacks = callbacks if callbacks is not None else PairingCallbacks()
    agent = Agent(callbacks)
    agent_path = f"/org/bleak/agent/{os.getpid()}/{id(agent)}"
    capability = _capability_name(io_capability(callbacks))

    async with AsyncExitStack() as stack:
        bus.export(agent_path, agent)
        stack.callback(bus.unexport, agent_path, agent)
        await _register_agent(bus, agent_path, capability)
        stack.push_async_callback(_unregister_agent, bus, agent_path)
        yield
