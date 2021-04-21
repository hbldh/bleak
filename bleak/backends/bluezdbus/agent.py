# -*- coding: utf-8 -*-
"""
BLE Pairing Agent for BlueZ on Linux
"""
import asyncio
import enum
import logging
import time
from typing import Optional

from dbus_next import DBusError
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from dbus_next.message import Message
from dbus_next.service import ServiceInterface, method

from bleak.backends.bluezdbus import defs
from bleak.backends.bluezdbus.utils import assert_reply

logger = logging.getLogger(__name__)

# https://python-dbus-next.readthedocs.io/en/latest/type-system/index.html
DBusObject = "o"
DBusString = "s"
DBusUInt16 = "q"
DBusUInt32 = "u"


class IOCapability(enum.Enum):
    """I/O capabilities of this device, used for determining pairing method"""

    DISPLAY_ONLY = "DisplayOnly"
    DISPLAY_YES_NO = "DisplayYesNo"
    KEYBOARD_ONLY = "KeyboardOnly"
    NO_IO = "NoInputNoOutput"
    KEYBOARD_DISPLAY = "KeyboardDisplay"


class PairingAgentBlueZDBus(ServiceInterface):
    """Agent for BlueZ pairing requests

    Implemented by using the `BlueZ DBUS Agent API <https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/agent-api.txt>`_.

    Args:
        io_capabilities (`Capability`): I/O capabilities of this device, used for determining pairing method.
    """

    def __init__(self, io_capabilities: IOCapability = IOCapability.KEYBOARD_DISPLAY):
        super().__init__(defs.AGENT_INTERFACE)

        # D-Bus message bus
        self._bus: Optional[MessageBus] = None
        # Path can be anything as long as it is unique
        self._path = f"/org/bluez/agent{time.time() * 1000:.0f}"
        # IO capabilities are required when the agent is registered
        self._io_capabilities = io_capabilities

        self.pin: Optional[str] = None
        """A string of 1-16 alphanumeric characters length for Pin Pairing, if supported."""
        self.passkey: Optional[int] = None
        """A numeric value between 0-999999 for Passkey Pairing, if supported."""

    def __del__(self) -> None:
        if self._bus:
            asyncio.ensure_future(self.unregister())

    async def __aenter__(self) -> "PairingAgentBlueZDBus":
        return await self.register()

    async def __aexit__(self, *exc_info) -> None:
        await self.unregister()

    async def register(self) -> "PairingAgentBlueZDBus":
        """
        Register the Agent for handling pairing requests

        Every application can register its own (and only one) agent and for all
        actions triggered by that application its agent is used. If an application
        chooses to not register an agent, the default system agent is used.
        """
        if self._bus:
            # An application can only register one agent. Multiple agents per application is not
            # supported and would raise error if not handled here.
            return self
        # Create system bus
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        # Make this Agent interface available on the given object path
        bus.export(self._path, self)
        # Register the Agent
        reply = await bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path="/org/bluez",
                interface=defs.AGENT_MANAGER_INTERFACE,
                member="RegisterAgent",
                signature="os",
                body=[self._path, self._io_capabilities.value],
            )
        )
        assert_reply(reply)
        # There is no need to register this agent as the default pairing agent using RequestDefaultAgent,
        # because it will be used for all pairing requests for this application after RegisterAgent.
        logger.debug(f"Pairing Agent registered on {self._path}")
        self._bus = bus
        return self

    async def unregister(self) -> None:
        """
        Unregister the agent that has been previously registered
        """
        # This method can be called multiple times, it is OK if agent is not registered anymore.
        if not self._bus:
            return

        reply = await self._bus.call(
            Message(
                destination=defs.BLUEZ_SERVICE,
                path="/org/bluez",
                interface=defs.AGENT_MANAGER_INTERFACE,
                member="UnregisterAgent",
                signature="o",
                body=[self._path],
            )
        )
        assert_reply(reply)

        self._bus.unexport(self._path)
        self._bus.disconnect()
        self._bus = None
        logger.debug(f"Pairing Agent {self._path} unregistered")

    @method(name="Release")
    def _release(self):
        """
        This method gets called when the service daemon
        unregisters the agent. An agent can use it to do
        cleanup tasks. There is no need to unregister the
        agent, because when this method gets called it has
        already been unregistered.
        """
        logger.debug(f"{self._path}::Release()")

    @method(name="RequestPinCode")
    def _request_pin_code(self, device: DBusObject) -> DBusString:
        """
        This method gets called when the service daemon
        needs to get the passkey for an authentication.

        The return value should be a string of 1-16 characters
        length. The string can be alphanumeric.

        Possible errors: org.bluez.Error.Rejected
                         org.bluez.Error.Canceled
        """
        logger.debug(f"{self._path}::RequestPinCode({device})->{self.pin}")

        if self.pin is None:
            raise DBusError(
                f"{defs.BLUEZ_SERVICE}.Error.Rejected", "Pin pairing rejected"
            )

        return self.pin

    @method(name="DisplayPinCode")
    def _display_pin_code(self, device: DBusObject, pincode: DBusString):
        """
        This method gets called when the service daemon
        needs to display a pincode for an authentication.

        An empty reply should be returned. When the pincode
        needs no longer to be displayed, the Cancel method
        of the agent will be called.

        This is used during the pairing process of keyboards
        that don't support Bluetooth 2.1 Secure Simple Pairing,
        in contrast to DisplayPasskey which is used for those
        that do.

        This method will only ever be called once since
        older keyboards do not support typing notification.

        Note that the PIN will always be a 6-digit number,
        zero-padded to 6 digits. This is for harmony with
        the later specification.

        Possible errors: org.bluez.Error.Rejected
                         org.bluez.Error.Canceled
        """
        logger.debug(f"{self._path}::DisplayPinCode({device})->{pincode}")

    @method(name="RequestPasskey")
    def _request_passkey(self, device: DBusObject) -> DBusUInt32:
        """
        This method gets called when the service daemon
        needs to get the passkey for an authentication.

        The return value should be a numeric value
        between 0-999999.

        Possible errors: org.bluez.Error.Rejected
                         org.bluez.Error.Canceled
        """
        logger.debug(f"{self._path}::RequestPasskey({device})->{self.passkey}")

        if self.passkey is None:
            raise DBusError(
                f"{defs.BLUEZ_SERVICE}.Error.Rejected", "Passkey pairing rejected"
            )

        return self.passkey

    @method(name="DisplayPasskey")
    def _display_passkey(
        self, device: DBusObject, passkey: DBusUInt32, entered: DBusUInt16
    ):
        """
        This method gets called when the service daemon
        needs to display a passkey for an authentication.

        The entered parameter indicates the number of already
        typed keys on the remote side.

        An empty reply should be returned. When the passkey
        needs no longer to be displayed, the Cancel method
        of the agent will be called.

        During the pairing process this method might be
        called multiple times to update the entered value.

        Note that the passkey will always be a 6-digit number,
        so the display should be zero-padded at the start if
        the value contains less than 6 digits.
        """
        logger.debug(f"{self._path}::DisplayPasskey({device}, {passkey}, {entered})")

    @method(name="RequestConfirmation")
    def _request_confirmation(self, device: DBusObject, passkey: DBusUInt32):
        """
        This method gets called when the service daemon
        needs to confirm a passkey for an authentication.

        To confirm the value it should return an empty reply
        or an error in case the passkey is invalid.

        Note that the passkey will always be a 6-digit number,
        so the display should be zero-padded at the start if
        the value contains less than 6 digits.

        Possible errors: org.bluez.Error.Rejected
                         org.bluez.Error.Canceled
        """
        confirm = True

        logger.debug(
            f"{self._path}::RequestConfirmation({device}, {passkey:06d})->{confirm}"
        )

        if not confirm:
            raise DBusError(f"{defs.BLUEZ_SERVICE}.Error.Rejected", "Passkey rejected")

    @method(name="RequestAuthorization")
    def _request_authorization(self, device: DBusObject):
        """
        This method gets called to request the user to
        authorize an incoming pairing attempt which
        would in other circumstances trigger the just-works
        model, or when the user plugged in a device that
        implements cable pairing. In the latter case, the
        device would not be connected to the adapter via
        Bluetooth yet.

        Possible errors: org.bluez.Error.Rejected
                         org.bluez.Error.Canceled
        """
        authorize = True

        logger.debug(f"{self._path}::RequestAuthorization({device})->{authorize}")

        if not authorize:
            raise DBusError(
                f"{defs.BLUEZ_SERVICE}.Error.Rejected", "Device unauthorized"
            )

    @method(name="AuthorizeService")
    def _authorize_service(self, device: DBusObject, uuid: DBusString):
        """
        This method gets called when the service daemon
        needs to authorize a connection/service request.

        Possible errors: org.bluez.Error.Rejected
                         org.bluez.Error.Canceled
        """
        authorize = True

        logger.debug(f"{self._path}::AuthorizeService({device}, {uuid})->{authorize}")

        if not authorize:
            raise DBusError(
                f"{defs.BLUEZ_SERVICE}.Error.Rejected", "Connection rejected"
            )

    @method(name="Cancel")
    def _cancel(self):
        """
        This method gets called to indicate that the agent
        request failed before a reply was returned.
        """
        logger.debug(f"{self._path}::Cancel()")


__all__ = ("logger", "IOCapability", "PairingAgentBlueZDBus")

# If this file is run as __main__ or imported without ever starting the event loop, the following warning will occur:
# Start the event loop if not yet running to prevent
#   sys:1: RuntimeWarning: coroutine 'PairingAgentBlueZDBus.unregister' was never awaited
